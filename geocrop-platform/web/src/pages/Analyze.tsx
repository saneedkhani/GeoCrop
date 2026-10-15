import { useQuery } from "@tanstack/react-query";
import { useRef, useState, type DragEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, post, type Job } from "../api/client";
import { useModels } from "../api/hooks";
import Icon from "../components/Icon";
import { API_URL } from "../config";
import { useAuth } from "../store/auth";

type UploadRes = { id: string; upload_url: string | null };
type Source = { id: string; aoi_id: string; kind: string; band_count: number; created_at: string };

function send(url: string, body: Blob | FormData, onProgress: (f: number) => void, method: string, token?: string | null) {
  return new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(method, url);
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total);
    xhr.onload = () => (xhr.status < 300 ? resolve() : reject(new Error(`Upload failed (${xhr.status}).`)));
    xhr.onerror = () => reject(new Error("Upload failed. Check your connection and try again."));
    xhr.send(body);
  });
}

const sourceName: Record<string, string> = { sentinel2_composite: "Sentinel-2 composite", sentinel2_upload: "Uploaded image" };

export default function Analyze() {
  const navigate = useNavigate();
  const token = useAuth((s) => s.token);
  const fileInput = useRef<HTMLInputElement>(null);
  const { data: models } = useModels();
  const { data: sources = [] } = useQuery({ queryKey: ["sources"], queryFn: () => api<Source[]>("/sources") });
  const runnable = (models?.models ?? []).filter((m) => m.enabled);
  const [selected, setSelected] = useState<string[]>(["cropland", "croptype"]);
  const [file, setFile] = useState<File | null>(null);
  const [drag, setDrag] = useState(false);
  const [location, setLocation] = useState("");
  const [date, setDate] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [pct, setPct] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggle = (k: string) => setSelected((s) => (s.includes(k) ? s.filter((x) => x !== k) : [...s, k]));
  const pick = (f: File | undefined) => {
    if (!f) return;
    if (!/\.tiff?$/i.test(f.name)) return setError("Choose a GeoTIFF (.tif or .tiff).");
    setError(null);
    setFile(f);
  };
  const onDrop = (e: DragEvent) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files[0]); };

  async function run() {
    if (!file) return setError("Choose a satellite image first.");
    if (!selected.length) return setError("Select at least one model to run.");
    setError(null);
    setBusy(true);
    try {
      const up = await post<UploadRes>("/uploads", { filename: file.name, size_bytes: file.size });
      if (up.upload_url) await send(up.upload_url, file, setPct, "PUT");
      else {
        const fd = new FormData();
        fd.append("file", file);
        await send(`${API_URL}/uploads/${up.id}/file`, fd, setPct, "POST", token);
      }
      const job = await post<Job>(`/uploads/${up.id}/complete`, {
        model_keys: selected, location: location || null, capture_date: date || null,
      });
      navigate(`/processing/${job.id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  }

  async function rerun() {
    if (!sourceId) return setError("Choose an image to re-analyse.");
    if (!selected.length) return setError("Select at least one model to run.");
    setError(null);
    try {
      const job = await post<Job>("/runs", { source_image_id: sourceId, model_keys: selected });
      navigate(`/processing/${job.id}`);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="page-center">
      <span className="icon-tile"><Icon name="upload" size={22} /></span>
      <h1>Process Satellite Data</h1>
      <p>Upload raw Sentinel-2 imagery to map cropland and classify crops. Results appear on the live map as soon as each model finishes.</p>

      <div className="card upload-card">
        <div className={`dropzone ${drag ? "drag" : ""}`} role="button" tabIndex={0}
          onClick={() => fileInput.current?.click()}
          onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && fileInput.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={onDrop}>
          <span className="icon-tile"><Icon name="image" size={22} /></span>
          <p><strong>Click to browse</strong> or drag a file here</p>
          <div className="hints"><span>GeoTIFF (.tif, .tiff)</span><span>Bands B2, B3, B4, B8, B11, B12 (+ NDVI)</span><span>Up to 500 MB</span></div>
          <input ref={fileInput} id="file" type="file" accept=".tif,.tiff" hidden onChange={(e) => pick(e.target.files?.[0])} />
        </div>
        {file && (
          <div className="file-pill">
            <Icon name="file" size={16} /> {file.name}
            <span className="faint small" style={{ marginLeft: "auto" }}>{(file.size / 1e6).toFixed(1)} MB</span>
          </div>
        )}

        <div className="sub-panel">
          <div className="sub-panel-head"><h3>Contextual Data</h3><span className="badge neutral">Optional</span></div>
          <div className="two-inputs">
            <input id="location" className="input" placeholder="Location (e.g. Grant County, WA)" value={location} onChange={(e) => setLocation(e.target.value)} />
            <input id="capture-date" className="input" type="date" aria-label="Image capture date" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
        </div>

        <div className="sub-panel">
          <div className="sub-panel-head"><h3>Analysis Models</h3><span className="small faint">Dependencies run automatically</span></div>
          <div className="model-options">
            {runnable.map((m) => {
              const stub = m.status === "stub";
              const on = !stub && selected.includes(m.key);
              return (
                <label key={m.key} className={`model-option ${on ? "on" : ""} ${stub ? "off" : ""}`}>
                  <input type="checkbox" id={`m-${m.key}`} checked={on} disabled={stub} onChange={() => toggle(m.key)} />
                  <span>
                    {m.name}
                    <span className="meta">{m.status === "stub" ? "Coming soon" : m.status === "example" ? "Vegetation index" : `Produces ${m.outputs.join(", ")}`}</span>
                  </span>
                </label>
              );
            })}
          </div>
        </div>

        {error && <div className="alert error">{error}</div>}
        {busy && <div className="progress"><div style={{ width: `${pct * 100}%` }} /></div>}
        <button className="btn-primary btn-lg btn-block" onClick={run} disabled={busy}>
          {busy ? `Uploading ${(pct * 100).toFixed(0)}%…` : <>Run Intelligence Analysis <Icon name="arrow" size={18} /></>}
        </button>
      </div>

      <div className="card upload-card">
        <div className="sub-panel-head"><h3>Re-analyse an existing image</h3></div>
        <p className="small muted">Run the selected models again on an image that is already in GeoCrop.</p>
        <div className="two-inputs">
          <select id="source" className="select" value={sourceId} onChange={(e) => setSourceId(e.target.value)}>
            <option value="">Choose an image…</option>
            {sources.map((s) => (
              <option key={s.id} value={s.id}>{sourceName[s.kind] ?? s.kind} · {new Date(s.created_at).toLocaleDateString()}</option>
            ))}
          </select>
          <button className="btn-secondary" onClick={rerun}>Run selected models</button>
        </div>
      </div>
    </div>
  );
}
