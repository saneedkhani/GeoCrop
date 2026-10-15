import type { CatalogLayer } from "../api/client";

const RAMPS: Record<string, string> = {
  rdylgn: "linear-gradient(90deg,#a50026,#f46d43,#fee08b,#d9ef8b,#66bd63,#006837)",
  viridis: "linear-gradient(90deg,#440154,#3b528b,#21918c,#5ec962,#fde725)",
};

export default function Legend({ layer }: { layer: CatalogLayer }) {
  const { style, legend } = layer;
  if (style.type === "categorical") {
    return (
      <ul className="legend">
        {legend.map((e) => (
          <li key={e.code ?? e.label} title={e.label}>
            <span className="swatch square" style={{ background: e.color }} />
            <span>{e.label}</span>
          </li>
        ))}
      </ul>
    );
  }
  if (style.type === "vector") {
    return (
      <>
        {legend.map((e) => <p key={e.label} className="legend-note">{e.label}</p>)}
        <ul className="legend">
          {Object.entries(style.colors ?? {}).map(([name, color]) => (
            <li key={name} title={name}><span className="swatch square" style={{ background: color }} /><span>{name}</span></li>
          ))}
        </ul>
      </>
    );
  }
  const ramp = legend.find((e) => e.ramp);
  if (ramp) {
    return (
      <div>
        <div className="ramp" style={{ background: RAMPS[ramp.ramp!] ?? "#94a3b8" }} />
        <div className="ramp-labels"><span>{ramp.min}</span><span>{ramp.label}</span><span>{ramp.max}</span></div>
      </div>
    );
  }
  return <>{legend.map((e) => <p key={e.label} className="legend-note">{e.label}</p>)}</>;
}
