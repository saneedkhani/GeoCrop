import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import Map, { Layer, NavigationControl, Popup, ScaleControl, Source } from "react-map-gl/maplibre";
import type { MapLayerMouseEvent, MapRef } from "react-map-gl/maplibre";
import { Link } from "react-router-dom";
import { api, fmt, HA_TO_ACRES, type CatalogLayer } from "../api/client";
import { useFields, useLayers, useStats } from "../api/hooks";
import { basemapStyle, BASEMAP_MODE, type BasemapId } from "../config";
import LayerPanel, { Dock } from "../map/LayerPanel";
import { groupRank, useLayerUi } from "../store/layers";

type Aoi = { id: string; name: string; bounds: [number, number, number, number] | null };
type PointValue = { layer_id: string; name: string; kind: string; value: number | null; label: string | null };
type Inspect = { lng: number; lat: number; values: PointValue[]; fields: Record<string, unknown>[]; loading: boolean };
type Bounds = [number, number, number, number];

const DEFAULT_ON = ["imagery", "croptype"];

function useTileTraffic() {
  const [t, setT] = useState({ count: 0, bytes: 0, lastMs: 0 });
  useEffect(() => {
    if (typeof PerformanceObserver === "undefined") return;
    const obs = new PerformanceObserver((list) => {
      let count = 0, bytes = 0, last = 0;
      for (const e of list.getEntries() as PerformanceResourceTiming[]) {
        if (e.name.includes("/tiles/") || e.name.includes(".pmtiles")) {
          count += 1; bytes += e.transferSize || 0; last = e.duration;
        }
      }
      if (count) setT((s) => ({ count: s.count + count, bytes: s.bytes + bytes, lastMs: last || s.lastMs }));
    });
    obs.observe({ type: "resource", buffered: true });
    return () => obs.disconnect();
  }, []);
  return t;
}

/** Tile URL with the crop filter applied (codes whose legend label matches the selected crop). */
function rasterTiles(l: CatalogLayer, crop: string): string {
  if (!crop || l.style.type !== "categorical") return l.tile_url;
  const codes = l.legend.filter((e) => e.label === crop).map((e) => e.code);
  return `${l.tile_url}?classes=${codes.length ? codes.join(",") : "none"}`;
}

function vectorFill(l: CatalogLayer): any {
  const entries = Object.entries(l.style.colors ?? {}).flat();
  return entries.length ? ["match", ["get", l.style.color_by ?? "class_name"], ...entries, "#888888"] : "#888888";
}

export default function LiveMap() {
  const mapRef = useRef<MapRef>(null);
  const [basemap, setBasemap] = useState<BasemapId>("satellite");
  const [unit, setUnit] = useState<"ac" | "ha">("ac");
  const [aoiId, setAoiId] = useState("");
  const [search, setSearch] = useState("");
  const [inspect, setInspect] = useState<Inspect | null>(null);
  const [zoom, setZoom] = useState(10);
  const { visible, opacity, setVisible, cropFilter, setCropFilter } = useLayerUi();
  const traffic = useTileTraffic();

  const { data: aois = [] } = useQuery({ queryKey: ["aois"], queryFn: () => api<Aoi[]>("/aois") });
  const { data: allLayers = [], isLoading, error } = useLayers();

  useEffect(() => { if (!aoiId && aois.length) setAoiId(aois[0].id); }, [aois, aoiId]);
  const aoi = aois.find((a) => a.id === aoiId);

  const layers = useMemo(
    () => allLayers.filter((l) => l.aoi_id === aoiId).sort((a, b) => groupRank(a.group) - groupRank(b.group)),
    [allLayers, aoiId],
  );
  const cropLayer = layers.find((l) => l.kind === "croptype");
  const { data: stats } = useStats(cropLayer?.id);
  const { data: fields = [] } = useFields(aoiId || undefined, search);
  const cropNames = (cropLayer?.legend ?? []).map((e) => e.label);

  // First view of an area: show its imagery and crop type so the map is never empty.
  useEffect(() => {
    if (!layers.length || layers.some((l) => visible[l.id] !== undefined)) return;
    const seen = new Set<string>();
    for (const l of layers) {
      if (DEFAULT_ON.includes(l.kind) && !seen.has(l.kind)) { setVisible(l.id, true); seen.add(l.kind); }
    }
  }, [layers, visible, setVisible]);

  const fit = (b: Bounds | null | undefined) => {
    if (b) mapRef.current?.fitBounds([[b[0], b[1]], [b[2], b[3]]], { padding: 40, duration: 800 });
  };
  useEffect(() => { fit(aoi?.bounds); }, [aoi?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const area = (ha: number) => (unit === "ha" ? ha : ha * HA_TO_ACRES);
  const unitLabel = unit === "ha" ? "ha" : "ac";
  const visibleCount = layers.filter((l) => visible[l.id]).length;
  const interactive = layers.filter((l) => l.format === "pmtiles" && visible[l.id]).map((l) => `fill-${l.id}`);

  async function onClick(e: MapLayerMouseEvent) {
    const { lng, lat } = e.lngLat;
    const feats = (e.features ?? []).map((f) => f.properties as Record<string, unknown>);
    const ids = layers.filter((l) => visible[l.id] && l.format === "cog").map((l) => l.id);
    setInspect({ lng, lat, values: [], fields: feats, loading: ids.length > 0 });
    if (!ids.length) return;
    try {
      const res = await api<{ values: PointValue[] }>(`/point?lng=${lng}&lat=${lat}&layers=${ids.join(",")}`);
      setInspect({ lng, lat, values: res.values, fields: feats, loading: false });
    } catch {
      setInspect({ lng, lat, values: [], fields: feats, loading: false });
    }
  }

  return (
    <div className="workspace">
      <aside className="ws-sidebar">
        <div className="ws-header">
          <Link to="/" className="ws-brand">GeoCrop</Link>
          <nav className="ws-nav">
            <Link to="/">Home</Link>
            <Link to="/dashboard">Dashboard</Link>
            <Link to="/analyze">Analyze</Link>
          </nav>
        </div>

        <div className="ws-scope">
          <span className="scope-label">Area</span>
          <select id="aoi-select" className="scope-select" value={aoiId} onChange={(e) => setAoiId(e.target.value)}>
            {aois.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        </div>
        <div className="livestrip">
          <span className="live-dot" />
          <strong>{fields.length.toLocaleString()}</strong> field regions ·
          <strong>{stats ? fmt(area(stats.total_area_ha)) : "–"}</strong> {unitLabel} classified
        </div>

        <LayerPanel layers={layers} onZoom={(l) => fit(l.bounds)} />

        <Dock title="Basemap panel" icon="map" defaultOpen={false}>
          {BASEMAP_MODE === "provider" ? (
            (["satellite", "streets"] as BasemapId[]).map((b) => (
              <label key={b} className="basemap-row">
                <input type="radio" name="basemap" checked={basemap === b} onChange={() => setBasemap(b)} />
                {b === "satellite" ? "Satellite" : "Streets"}
              </label>
            ))
          ) : (
            <p className="legend-note">OpenStreetMap streets. Add a MapTiler or Esri key in the settings to enable satellite imagery.</p>
          )}
        </Dock>

        <div className="ws-scope">
          <span className="scope-label">Unit</span>
          <select id="unit-select" className="scope-select" value={unit} onChange={(e) => setUnit(e.target.value as "ac" | "ha")}>
            <option value="ac">acres</option>
            <option value="ha">hectares</option>
          </select>
        </div>
        <div className="ws-divider" />

        <section className="ws-section">
          <h4>Crop ranking in this area</h4>
          <table className="rank-table">
            <thead><tr><th>#</th><th>Crop</th><th className="num">Area ({unitLabel})</th></tr></thead>
            <tbody>
              {(stats?.rows ?? []).map((r, i) => (
                <tr key={r.class_name} className={cropFilter === r.class_name ? "selected" : ""}
                  onClick={() => setCropFilter(cropFilter === r.class_name ? "" : r.class_name ?? "")}>
                  <td className="faint">{i + 1}</td>
                  <td><span className="crop"><span className="swatch" style={{ background: r.color ?? "#94a3b8" }} />{r.class_name}</span></td>
                  <td className="num">{fmt(area(r.area_ha))}</td>
                </tr>
              ))}
              {!stats && <tr><td colSpan={3} className="faint">No crop-type layer in this area.</td></tr>}
            </tbody>
          </table>
        </section>

        <section className="ws-section">
          <h4>Fields ({fields.length.toLocaleString()})</h4>
          <input id="field-search" className="input field-search" placeholder="Search by crop, e.g. Apples"
            value={search} onChange={(e) => setSearch(e.target.value)} />
          <ul className="field-list">
            {fields.map((f) => (
              <li key={f.id} className="field-item" onClick={() => fit(f.bbox)}>
                <span className="swatch" style={{ background: cropLayer?.legend.find((e) => e.label === f.class_name)?.color ?? "#94a3b8" }} />
                Field {f.field_id} · {f.class_name}
                <span className="meta">{fmt(area(f.area_ha), 1)} {unitLabel}</span>
              </li>
            ))}
            {!fields.length && <li className="field-empty">No field regions match.</li>}
          </ul>
        </section>
      </aside>

      <div className="ws-map">
        {isLoading && <div className="map-message">Loading layers…</div>}
        {error && <div className="map-message error">{(error as Error).message}</div>}
        <Map
          ref={mapRef}
          initialViewState={{ longitude: -119.64, latitude: 47.1, zoom: 10 }}
          mapStyle={basemapStyle(basemap) as any}
          onLoad={() => fit(aoi?.bounds)}
          onZoomEnd={(e) => setZoom(e.viewState.zoom)}
          onClick={onClick}
          interactiveLayerIds={interactive}
          style={{ position: "absolute", inset: 0 }}
        >
          <NavigationControl position="top-right" />
          <ScaleControl position="bottom-right" />
          {layers.map((l) => {
            const vis = visible[l.id] ? "visible" : "none";
            const op = opacity[l.id] ?? 0.85;
            if (l.format === "cog") {
              const tiles = rasterTiles(l, cropFilter);
              return (
                <Source key={`${l.id}-${tiles}`} id={`src-${l.id}`} type="raster" tiles={[tiles]} tileSize={256}
                  minzoom={l.min_zoom} maxzoom={14} bounds={l.bounds ?? undefined}>
                  <Layer id={`r-${l.id}`} type="raster" layout={{ visibility: vis }}
                    paint={{ "raster-opacity": op, "raster-resampling": l.style.type === "categorical" ? "nearest" : "linear" }} />
                </Source>
              );
            }
            const sourceLayer = l.style.source_layer ?? "fields";
            const filter: any = cropFilter ? ["==", ["get", "class_name"], cropFilter] : ["has", "class_name"];
            return (
              <Source key={l.id} id={`src-${l.id}`} type="vector" url={l.tile_url}>
                <Layer id={`fill-${l.id}`} type="fill" source-layer={sourceLayer} filter={filter}
                  layout={{ visibility: vis }} paint={{ "fill-color": vectorFill(l), "fill-opacity": op * 0.55 }} />
                <Layer id={`line-${l.id}`} type="line" source-layer={sourceLayer} filter={filter}
                  layout={{ visibility: vis }} paint={{ "line-color": l.style.outline ?? "#ffffff", "line-width": 0.8, "line-opacity": op }} />
              </Source>
            );
          })}
          {inspect && (
            <Popup longitude={inspect.lng} latitude={inspect.lat} onClose={() => setInspect(null)} closeOnClick={false} maxWidth="300px">
              <div className="inspect">
                <p className="coord">{inspect.lat.toFixed(5)}, {inspect.lng.toFixed(5)}</p>
                {inspect.loading && <p className="small">Reading values…</p>}
                {inspect.values.map((v) => (
                  <div key={v.layer_id} className="row">
                    <span>{v.name}</span>
                    <strong>{v.label ?? (v.value === null ? "No data" : v.value.toFixed(3))}</strong>
                  </div>
                ))}
                {inspect.fields.slice(0, 1).map((f, i) => (
                  <div key={i} className="row">
                    <span>Field region #{String(f.field_id)}</span>
                    <strong>{String(f.class_name)} · {fmt(area(Number(f.area_ha)), 1)} {unitLabel}</strong>
                  </div>
                ))}
                {!inspect.loading && !inspect.values.length && !inspect.fields.length && (
                  <p className="small">Turn on a result layer to inspect values here.</p>
                )}
              </div>
            </Popup>
          )}
        </Map>

        <div className="map-chip">
          <span>Filter</span>
          <select id="crop-filter" value={cropFilter} onChange={(e) => setCropFilter(e.target.value)} aria-label="Filter crops">
            <option value="">All crops</option>
            {cropNames.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>

        <div className="live-panel">
          <Dock title="Live map panel" icon="activity">
            <div className="row"><span>Status</span><span><span className="live-dot" style={{ display: "inline-block", marginRight: 6 }} />Live</span></div>
            <div className="row"><span>Layers on</span><span>{visibleCount} of {layers.length}</span></div>
            <div className="row"><span>Tiles loaded</span><span>{traffic.count} · {fmt(traffic.bytes / 1024)} KB</span></div>
            <div className="row"><span>Last tile</span><span>{traffic.lastMs ? `${fmt(traffic.lastMs)} ms` : "–"}</span></div>
            <div className="row"><span>Zoom</span><span>{zoom.toFixed(1)}</span></div>
          </Dock>
        </div>
      </div>
    </div>
  );
}
