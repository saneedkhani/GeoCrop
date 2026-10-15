import { useQuery } from "@tanstack/react-query";
import { api, type CatalogLayer, type FieldRow, type LayerStats, type ModelInfo } from "./client";

export const useLayers = () =>
  useQuery({ queryKey: ["layers"], queryFn: () => api<CatalogLayer[]>("/layers") });

export const useModels = () =>
  useQuery({ queryKey: ["models"], queryFn: () => api<{ models: ModelInfo[]; registry_errors: string[] }>("/models") });

export const useStats = (layerId: string | undefined) =>
  useQuery({ queryKey: ["stats", layerId], queryFn: () => api<LayerStats>(`/stats?layer=${layerId}`), enabled: !!layerId });

export const useFields = (aoi: string | undefined, q: string) =>
  useQuery({
    queryKey: ["fields", aoi, q],
    queryFn: () => api<FieldRow[]>(`/fields?limit=200${aoi ? `&aoi=${aoi}` : ""}${q ? `&q=${encodeURIComponent(q)}` : ""}`),
  });

/** The reference crop-type layer: the public AOI 1 result, falling back to the newest one. */
export function pickCropTypeLayer(layers: CatalogLayer[]): CatalogLayer | undefined {
  const crop = layers.filter((l) => l.kind === "croptype");
  return crop[0] ?? undefined;
}
