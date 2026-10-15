// The only place the basemap provider appears. Change provider = change env vars.
const env = import.meta.env;

export const API_URL: string = env.VITE_API_URL || "/api/v1";
// false (default): the app opens straight to the map as the guest account; sign-in is optional.
export const AUTH_REQUIRED: boolean = env.VITE_AUTH_REQUIRED === "true";
export const BASEMAP_MODE: "provider" | "osm_fallback" =
  env.VITE_BASEMAP_MODE === "provider" && env.VITE_BASEMAP_KEY ? "provider" : "osm_fallback";

const withKey = (url: string) => `${url}${url.includes("?") ? "&" : "?"}key=${env.VITE_BASEMAP_KEY}`;

const osmStyle = {
  version: 8 as const,
  sources: {
    osm: {
      type: "raster" as const,
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      maxzoom: 19,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [{ id: "osm", type: "raster" as const, source: "osm" }],
};

export type BasemapId = "satellite" | "streets";

export function basemapStyle(id: BasemapId): string | typeof osmStyle {
  if (BASEMAP_MODE === "osm_fallback") return osmStyle;
  return withKey(id === "satellite" ? env.VITE_BASEMAP_SAT_STYLE : env.VITE_BASEMAP_STREETS_STYLE);
}
