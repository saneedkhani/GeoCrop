import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { BASEMAP_MODE } from "../config";

type Health = {
  status: string;
  services: Record<string, { ok: boolean; detail: string; errors?: string[] }>;
  degraded_modes: string[];
};

const NAMES: Record<string, string> = { database: "Database", redis: "Job queue", storage: "File storage", tiles: "Map tile service", models: "Model registry" };

const ARCH = [
  { box: "React + MapLibre GL", where: "web/", role: "Website, live map, dashboard, analysis" },
  { box: "Nginx", where: "web/nginx.conf", role: "Single entry point, map tile cache" },
  { box: "FastAPI", where: "backend/app/", role: "Accounts, catalog, statistics, uploads, jobs" },
  { box: "TiTiler / rio-tiler", where: "tiles/", role: "Turns result rasters into map tiles" },
  { box: "PostgreSQL + PostGIS", where: "backend/app/db/", role: "Areas, runs, layers, statistics, fields" },
  { box: "Celery + Redis", where: "backend/app/workers/", role: "Background image processing and model runs" },
  { box: "MinIO (S3)", where: "docker-compose.yml", role: "Imagery, results and vector tiles" },
  { box: "Model registry", where: "backend/model_registry/", role: "Plug-in analysis models" },
];

export default function Status() {
  const { data, isLoading, refetch } = useQuery({ queryKey: ["health"], queryFn: () => api<Health>("/health"), refetchInterval: 15000 });
  const notes = [...(data?.degraded_modes ?? [])];
  if (BASEMAP_MODE === "osm_fallback") notes.push("Basemap: OpenStreetMap streets (set VITE_BASEMAP_KEY to enable satellite imagery)");

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>System Status</h1>
          <p>Live health of every service behind GeoCrop.</p>
        </div>
        <button className="btn-secondary btn-sm" onClick={() => refetch()}>Refresh</button>
      </div>
      {isLoading && <p className="muted">Checking services…</p>}
      {data && (
        <div className="service-grid">
          {Object.entries(data.services).map(([name, s]) => (
            <div key={name} className="card service-card">
              <span className={`status-dot ${s.ok ? "ok" : ""}`} />
              <div>
                <strong>{NAMES[name] ?? name}</strong>
                <p className="small muted">{s.detail}</p>
                {s.errors?.map((e) => <p key={e} className="small error-text">{e}</p>)}
              </div>
            </div>
          ))}
        </div>
      )}
      {notes.length > 0 && (
        <section className="card">
          <div className="card-head"><h3>Configuration notes</h3></div>
          <div className="card-body"><ul className="ordered-steps">{notes.map((n) => <li key={n}>{n}</li>)}</ul></div>
        </section>
      )}
      <section className="card">
        <div className="card-head"><h3>Architecture</h3><span className="small faint">Each component and where it lives in the code</span></div>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Component</th><th>Code</th><th>Role</th></tr></thead>
            <tbody>{ARCH.map((a) => <tr key={a.box}><td><strong>{a.box}</strong></td><td><code>{a.where}</code></td><td>{a.role}</td></tr>)}</tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
