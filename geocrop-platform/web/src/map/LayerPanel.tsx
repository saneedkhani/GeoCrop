import { useState, type ReactNode } from "react";
import type { CatalogLayer } from "../api/client";
import Icon from "../components/Icon";
import { groupRank, useLayerUi } from "../store/layers";
import Legend from "./Legend";

export function Dock({ title, icon, children, defaultOpen = true, className = "" }:
  { title: string; icon: string; children: ReactNode; defaultOpen?: boolean; className?: string }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className={`dock ${open ? "" : "collapsed"} ${className}`}>
      <button className="dock-head" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span className="dock-icon"><Icon name={icon} size={15} /></span>
        {title}
        <Icon name="chevron" size={15} className="chev" />
      </button>
      <div className="dock-body">{children}</div>
    </section>
  );
}

const describe = (l: CatalogLayer) =>
  `${l.format === "cog" ? "Raster tiles" : "Vector tiles"}${l.created_at ? ` · ${new Date(l.created_at).toLocaleDateString()}` : ""}`;

export default function LayerPanel({ layers, onZoom }: { layers: CatalogLayer[]; onZoom: (l: CatalogLayer) => void }) {
  const { visible, opacity, toggle, setOpacity } = useLayerUi();
  const groups = [...new Set(layers.map((l) => l.group))].sort((a, b) => groupRank(a) - groupRank(b));

  return (
    <Dock title="Layer panel" icon="layers">
      {!layers.length && <p className="legend-note">No layers in this area yet. Analyze an image to create some.</p>}
      {groups.map((g) => (
        <div key={g}>
          <div className="dock-group">{g}</div>
          {layers.filter((l) => l.group === g).map((l) => {
            const on = !!visible[l.id];
            return (
              <div key={l.id} className={`dock-layer ${on ? "on" : ""}`} style={{ marginTop: ".4rem" }}>
                <label>
                  <input id={`toggle-${l.id}`} type="checkbox" checked={on} onChange={() => toggle(l.id)} />
                  <span><span className="lname">{l.name}</span><span className="lmeta">{describe(l)}</span></span>
                </label>
                {on && (
                  <div className="dock-controls">
                    <div className="opacity-row">
                      <span>Opacity</span>
                      <input id={`opacity-${l.id}`} type="range" min={0} max={1} step={0.05}
                        value={opacity[l.id] ?? 0.85} onChange={(e) => setOpacity(l.id, Number(e.target.value))} />
                      <button className="link-btn" onClick={() => onZoom(l)}>Zoom to</button>
                    </div>
                    <Legend layer={l} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ))}
    </Dock>
  );
}
