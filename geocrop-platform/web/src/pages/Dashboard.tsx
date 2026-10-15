import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { api, fmt, HA_TO_ACRES } from "../api/client";
import { useLayers, useModels, useStats } from "../api/hooks";
import Icon from "../components/Icon";

type Aoi = { id: string; name: string };

export default function Dashboard() {
  const [unit, setUnit] = useState<"ac" | "ha">("ac");
  const [aoiId, setAoiId] = useState("");
  const [layerId, setLayerId] = useState("");
  const { data: aois = [] } = useQuery({ queryKey: ["aois"], queryFn: () => api<Aoi[]>("/aois") });
  const { data: layers = [] } = useLayers();
  const { data: models } = useModels();

  useEffect(() => { if (!aoiId && aois.length) setAoiId(aois[0].id); }, [aois, aoiId]);
  const statLayers = useMemo(
    () => layers.filter((l) => l.aoi_id === aoiId && l.format === "cog" && l.style.type === "categorical"),
    [layers, aoiId],
  );
  useEffect(() => {
    if (!statLayers.some((l) => l.id === layerId)) {
      setLayerId((statLayers.find((l) => l.kind === "croptype") ?? statLayers[0])?.id ?? "");
    }
  }, [statLayers, layerId]);

  const { data: stats, isLoading } = useStats(layerId || undefined);
  const area = (ha: number) => (unit === "ha" ? ha : ha * HA_TO_ACRES);
  const unitWord = unit === "ha" ? "Hectares" : "Acres";
  const cropland = models?.models.find((m) => m.key === "cropland")?.last_run_metrics;
  const croptype = models?.models.find((m) => m.key === "croptype")?.last_run_metrics;
  const rows = stats?.rows ?? [];
  const maxPct = Math.max(1, ...rows.map((r) => r.pct ?? 0));

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Analytics Dashboard</h1>
          <p>Monitor crop insights across every analysed area. Figures are pre-computed when each result is published.</p>
        </div>
        <div className="filter-bar">
          <div className="filter-field">
            <label htmlFor="dash-aoi">Area</label>
            <select id="dash-aoi" className="select" value={aoiId} onChange={(e) => setAoiId(e.target.value)}>
              {aois.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </div>
          <div className="filter-field">
            <label htmlFor="dash-layer">Layer</label>
            <select id="dash-layer" className="select" value={layerId} onChange={(e) => setLayerId(e.target.value)}>
              {statLayers.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
          </div>
          <div className="filter-field" style={{ minWidth: 0 }}>
            <label>Unit</label>
            <div className="segmented">
              <button className={unit === "ac" ? "active" : ""} onClick={() => setUnit("ac")}>Acres</button>
              <button className={unit === "ha" ? "active" : ""} onClick={() => setUnit("ha")}>Hectares</button>
            </div>
          </div>
        </div>
      </div>

      <div className="stat-grid">
        <div className="card stat-card">
          <span className="icon-tile"><Icon name="leaf" size={22} /></span>
          <div><div className="label">Classes in layer</div><div className="value">{stats ? rows.length : "–"}</div></div>
        </div>
        <div className="card stat-card">
          <span className="icon-tile sky"><Icon name="grid" size={22} /></span>
          <div><div className="label">Total Land Area ({unitWord})</div><div className="value">{stats ? fmt(area(stats.total_area_ha)) : "–"}</div></div>
        </div>
        <div className="card stat-card">
          <span className="icon-tile gold"><Icon name="bars" size={22} /></span>
          <div>
            <div className="label">Cropland Accuracy</div>
            <div className="value">{cropland?.accuracy ? `${fmt(cropland.accuracy * 100, 1)}%` : "–"}</div>
            <div className="sub">held-out pixels</div>
          </div>
        </div>
        <div className="card stat-card">
          <span className="icon-tile"><Icon name="cpu" size={22} /></span>
          <div>
            <div className="label">Crop Type Accuracy</div>
            <div className="value">{croptype?.accuracy ? `${fmt(croptype.accuracy * 100, 1)}%` : "–"}</div>
            <div className="sub">held-out pixels</div>
          </div>
        </div>
      </div>

      <div className="dash-grid">
        <section className="card">
          <div className="card-head"><h3>Crop Distribution</h3><span className="small faint">Share of classified area</span></div>
          <div className="card-body">
            {isLoading && <p className="muted">Loading…</p>}
            <ul className="dist-list">
              {rows.map((r) => (
                <li key={r.class_name} className="dist-row">
                  <span className="swatch" style={{ background: r.color ?? "#94a3b8" }} />
                  <span className="name" title={r.class_name ?? ""}>{r.class_name}</span>
                  <span className="dist-track"><span className="dist-fill" style={{ display: "block", width: `${((r.pct ?? 0) / maxPct) * 100}%`, background: r.color ?? "#94a3b8" }} /></span>
                  <span className="pct">{r.pct !== null ? `${fmt(r.pct, 1)}%` : "–"}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="card">
          <div className="card-head"><h3>Detailed Crop Breakdown</h3><span className="small faint">Area and share by class</span></div>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr><th>Classification</th><th className="num">Area ({unit})</th><th className="num">Pixels (30 m)</th><th className="num">% of total</th></tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.class_name}>
                    <td><span className="crop-cell"><span className="swatch" style={{ background: r.color ?? "#94a3b8" }} />{r.class_name}</span></td>
                    <td className="num">{fmt(area(r.area_ha), 1)}</td>
                    <td className="num">{fmt(r.pixel_count)}</td>
                    <td className="num">{r.pct !== null ? `${fmt(r.pct, 1)}%` : "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="note">
            Accuracy is measured on a random 20% of pixels from the area the models were trained on, so it is an
            optimistic estimate. Validation on new regions is part of the next model release.
          </p>
        </section>
      </div>
    </div>
  );
}
