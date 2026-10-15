import { API_URL } from "../config";
import { useAuth } from "../store/auth";

export type LegendEntry = { code?: number; label: string; color?: string; ramp?: string; min?: number; max?: number };

export type LayerStyle = {
  type: "categorical" | "continuous" | "rgb" | "vector";
  colormap?: Record<string, string>;
  source_layer?: string;
  color_by?: string;
  colors?: Record<string, string>;
  outline?: string;
};

export type CatalogLayer = {
  id: string;
  kind: string;
  group: string;
  name: string;
  format: "cog" | "pmtiles";
  run_id: string | null;
  aoi_id: string | null;
  bounds: [number, number, number, number] | null;
  min_zoom: number;
  max_zoom: number;
  style: LayerStyle;
  legend: LegendEntry[];
  version: number;
  tile_url: string;
  created_at: string | null;
};

export type JobStep = { name: string; status: "pending" | "running" | "done" | "skipped" | "failed" };
export type Job = {
  id: string;
  kind: string;
  status: string;
  progress: number;
  message: string | null;
  error: string | null;
  steps: JobStep[];
  created_at: string;
  finished_at: string | null;
};

export type ModelInfo = {
  key: string;
  name: string;
  task: string;
  version: string;
  status: "ready" | "stub" | "example";
  enabled: boolean;
  requires: string[];
  outputs: string[];
  input_bands: string[] | null;
  valid_regions: string[];
  notes: string | null;
  training: Record<string, string> | null;
  last_run_metrics: { accuracy?: number; macro_f1?: number; split?: string; note?: string } | null;
  class_scores: { label: string; precision: number; recall: number; f1: number; support: number }[];
};

export type FieldRow = { id: string; field_id: number; class_name: string; area_ha: number; bbox: [number, number, number, number] };

export type StatRow = { class_code: number | null; class_name: string | null; pixel_count: number; area_ha: number;
  pct: number | null; mean: number | null; color?: string | null };
export type LayerStats = { layer: CatalogLayer; total_area_ha: number; rows: StatRow[] };

export const HA_TO_ACRES = 2.47105;
export const fmt = (n: number, d = 0) =>
  n.toLocaleString(undefined, { maximumFractionDigits: d, minimumFractionDigits: d });

export class ApiError extends Error {}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = useAuth.getState().token;
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (res.status === 401) useAuth.getState().signOut();
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      msg = typeof body.detail === "string" ? body.detail : msg;
    } catch {
      /* keep default */
    }
    throw new ApiError(msg);
  }
  return res.json() as Promise<T>;
}

export const post = <T,>(path: string, body: unknown) => api<T>(path, { method: "POST", body: JSON.stringify(body) });
