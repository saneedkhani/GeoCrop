import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fmt, HA_TO_ACRES } from "../api/client";
import { pickCropTypeLayer, useFields, useLayers, useModels, useStats } from "../api/hooks";
import Icon from "../components/Icon";

const RAIL = [
  { id: "section-overview", label: "Overview", icon: "home" },
  { id: "section-how", label: "How it works", icon: "clock" },
  { id: "section-explore", label: "Explore platform", icon: "grid" },
  { id: "about", label: "About & mission", icon: "info" },
  { id: "section-crops", label: "Crop coverage", icon: "layers" },
  { id: "section-cta", label: "Get started", icon: "down" },
];

function PageRail() {
  const [expanded, setExpanded] = useState(false);
  const [active, setActive] = useState(RAIL[0].id);

  useEffect(() => {
    if (!("IntersectionObserver" in window)) return;
    const obs = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && setActive(e.target.id)),
      { rootMargin: "-40% 0px -55% 0px" },
    );
    RAIL.forEach((r) => {
      const el = document.getElementById(r.id);
      if (el) obs.observe(el);
    });
    return () => obs.disconnect();
  }, []);

  return (
    <nav className={`page-rail ${expanded ? "expanded" : ""}`} aria-label="On this page">
      <button className="rail-toggle" aria-label={expanded ? "Collapse menu" : "Expand menu"} aria-expanded={expanded}
        onClick={() => setExpanded(!expanded)}>
        <span /><span /><span />
      </button>
      <span className="rail-label">On this page</span>
      {RAIL.map((r) => (
        <a key={r.id} href={`#${r.id}`} className={`rail-link ${active === r.id ? "active" : ""}`}
          onClick={(e) => { e.preventDefault(); document.getElementById(r.id)?.scrollIntoView({ behavior: "smooth" }); }}>
          <Icon name={r.icon} size={16} /><span className="rail-text">{r.label}</span>
        </a>
      ))}
      <span className="rail-label">Quick action</span>
      <Link to="/analyze" className="rail-link cta"><Icon name="upload" size={16} /><span className="rail-text">Analyze imagery</span></Link>
    </nav>
  );
}

function HeroVisual({ label, sub }: { label: string; sub: string }) {
  return (
    <div className="hero-visual" aria-hidden="true">
      <svg viewBox="0 0 420 400">
        <defs>
          <pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse">
            <path d="M28 0H0V28" fill="none" stroke="rgba(255,255,255,0.06)" />
          </pattern>
        </defs>
        <rect width="420" height="400" fill="url(#grid)" />
        <g stroke="rgba(255,255,255,0.75)" strokeWidth="1.5">
          <polygon points="40,70 175,48 205,150 70,180" fill="#e6a817" opacity="0.92" />
          <polygon points="185,58 320,38 340,128 210,152" fill="#2e7d32" />
          <polygon points="45,190 210,164 232,262 62,290" fill="#1f77b4" opacity="0.9" />
          <polygon points="218,158 348,132 380,238 246,262" fill="#8c564b" opacity="0.9" />
          <polygon points="70,300 245,270 275,352 108,372" fill="#2e7d32" opacity="0.85" />
        </g>
        <line x1="0" y1="205" x2="420" y2="205" stroke="#22c55e" strokeWidth="2" opacity="0.55" />
        <circle cx="300" cy="200" r="6" fill="#fff" />
        <rect x="282" y="186" width="132" height="54" rx="8" fill="#fff" />
        <text x="294" y="208" fontFamily="Manrope, sans-serif" fontSize="11.5" fontWeight="800" fill="#0f172a">{label}</text>
        <text x="294" y="227" fontFamily="Manrope, sans-serif" fontSize="10" fontWeight="600" fill="#475569">{sub}</text>
      </svg>
    </div>
  );
}

// Field-row texture tinted with the crop's map colour (no stock photos needed).
const cropArt = (color: string) => ({
  background: `repeating-linear-gradient(115deg, ${color} 0 14px, color-mix(in srgb, ${color} 72%, #0f251d) 14px 22px)`,
});

export default function Home() {
  const { data: layers = [] } = useLayers();
  const { data: models } = useModels();
  const cropLayer = pickCropTypeLayer(layers);
  const { data: stats } = useStats(cropLayer?.id);
  const { data: fields = [] } = useFields(cropLayer?.aoi_id ?? undefined, "");

  const cropland = models?.models.find((m) => m.key === "cropland")?.last_run_metrics;
  const croptype = models?.models.find((m) => m.key === "croptype");
  const scores = Object.fromEntries((croptype?.class_scores ?? []).map((c) => [c.label, c]));
  const rows = (stats?.rows ?? []).filter((r) => r.class_name !== "Other crop");
  const topCrops = rows.slice(0, 4);
  const biggest = fields[0];

  return (
    <div className="home">
      <PageRail />
      <div className="home-body">
        <section className="hero geo-grid-bg" id="section-overview">
          <div className="hero-inner">
            <div>
              <span className="eyebrow"><span className="dot" /> Satellite crop intelligence</span>
              <h1>Know every field before you drive to it.</h1>
              <p className="hero-lede">
                GeoCrop reads Sentinel-2 satellite imagery to map cropland, classify the crop growing in every
                field and summarise it by area, all on a fast live map. New models plug straight into the platform
                as they are trained, starting with field boundaries and yield.
              </p>
              <div className="hero-actions">
                <Link to="/analyze" className="btn-primary btn-lg">Analyze Satellite Data</Link>
                <Link to="/map" className="btn-secondary btn-lg btn-on-dark">Explore Live Map</Link>
              </div>
              <dl className="hero-stats">
                <div><dt>Crop types classified</dt><dd>{stats ? rows.length : "–"}</dd></div>
                <div><dt>Area mapped</dt><dd>{stats ? `${fmt(stats.total_area_ha * HA_TO_ACRES / 1000, 0)}k ac` : "–"}</dd></div>
                <div><dt>Cropland accuracy</dt><dd>{cropland?.accuracy ? `${fmt(cropland.accuracy * 100, 0)}%` : "–"}</dd></div>
              </dl>
            </div>
            <HeroVisual
              label={biggest ? `Field ${biggest.field_id} · ${biggest.class_name}` : "Field · Crop"}
              sub={biggest ? `${fmt(biggest.area_ha * HA_TO_ACRES, 1)} acres` : "Loading…"} />
          </div>
        </section>

        <section className="section" id="section-how">
          <div className="section-head">
            <span className="section-tag">How GeoCrop works</span>
            <h2>From raw imagery to a crop map, in three steps</h2>
            <p>Upload a satellite image and GeoCrop does the rest: every result becomes a layer on the live map, with statistics ready on the dashboard.</p>
          </div>
          <div className="steps-grid">
            <div className="step-card">
              <span className="step-num">01</span>
              <h3>Upload imagery</h3>
              <p>Drop in a Sentinel-2 GeoTIFF with its location and capture date. It is checked, aligned and optimised for fast viewing automatically.</p>
            </div>
            <div className="step-card">
              <span className="step-num">02</span>
              <h3>Models map &amp; classify</h3>
              <p>The cropland model finds farmed land, then the crop-type model classifies every field. Progress is shown live while they run.</p>
            </div>
            <div className="step-card">
              <span className="step-num">03</span>
              <h3>Explore &amp; analyse</h3>
              <p>Results appear as toggleable layers on the live map, with crop areas, rankings and field lists on the dashboard.</p>
            </div>
          </div>
        </section>

        <section className="section" id="section-explore">
          <div className="action-grid">
            <Link to="/analyze" className="action-card">
              <span className="icon-tile"><Icon name="upload" size={22} /></span>
              <div><h3>Analyze Satellite Data</h3><p>Upload a new capture and run the mapping and classification models on it.</p></div>
              <span className="action-arrow" aria-hidden="true">&rarr;</span>
            </Link>
            <Link to="/map" className="action-card">
              <span className="icon-tile sky"><Icon name="map" size={22} /></span>
              <div><h3>Live Map View</h3><p>Browse cropland, crop types and field regions on an interactive map.</p></div>
              <span className="action-arrow" aria-hidden="true">&rarr;</span>
            </Link>
            <Link to="/dashboard" className="action-card">
              <span className="icon-tile gold"><Icon name="chart" size={22} /></span>
              <div><h3>Analytics Dashboard</h3><p>See crop areas, shares and model accuracy for every mapped region.</p></div>
              <span className="action-arrow" aria-hidden="true">&rarr;</span>
            </Link>
          </div>
        </section>

        <section className="section" id="about">
          <div className="section-head">
            <span className="section-tag">About GeoCrop</span>
            <h2>Our Story &amp; Mission</h2>
            <p>Bridging the gap between orbital satellite data and ground-level agricultural decision making.</p>
          </div>
          <div className="about-grid">
            <div className="about-card">
              <span className="icon-tile"><Icon name="search" size={22} /></span>
              <h3>The Problem We Solve</h3>
              <p>Traditional field surveying needs physical inspection, manual boundary sketching and slow seasonal sampling. GeoCrop replaces weeks of fieldwork with satellite analytics.</p>
            </div>
            <div className="about-card">
              <span className="icon-tile sky"><Icon name="satellite" size={22} /></span>
              <h3>Multispectral AI Engine</h3>
              <p>Our models read visible, near-infrared (NIR) and short-wave infrared (SWIR) reflectance from Sentinel-2, trained against the USDA Cropland Data Layer.</p>
            </div>
            <div className="about-card">
              <span className="icon-tile gold"><Icon name="plug" size={22} /></span>
              <h3>Built to Grow</h3>
              <p>Every model plugs into the platform the same way, so field boundaries, yield estimation and new regions arrive without rebuilding the product.</p>
            </div>
          </div>
        </section>

        <section className="section" id="section-crops">
          <div className="section-head">
            <span className="section-tag">Coverage</span>
            <h2>Supported Crops &amp; Metrics</h2>
            <p>The most widespread crops our crop-type model maps today, with their area and per-crop accuracy on held-out pixels.</p>
          </div>
          <div className="crop-grid">
            {topCrops.map((r) => {
              const s = scores[r.class_name ?? ""];
              return (
                <article key={r.class_name} className="crop-card">
                  <div className="crop-art" style={cropArt(r.color ?? "#1e6f47")}>
                    {s && <span className="crop-badge">F1 score {fmt(s.f1, 2)}</span>}
                  </div>
                  <div className="crop-body">
                    <h3>{r.class_name}</h3>
                    <dl className="crop-metrics">
                      <div><dt>Mapped area</dt><dd>{fmt(r.area_ha * HA_TO_ACRES)} ac</dd></div>
                      <div><dt>Share of cropland</dt><dd>{r.pct !== null ? `${fmt(r.pct, 1)}%` : "–"}</dd></div>
                      {s && <div><dt>Precision / recall</dt><dd>{fmt(s.precision, 2)} / {fmt(s.recall, 2)}</dd></div>}
                    </dl>
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <section className="final-cta geo-grid-bg" id="section-cta">
          <h2>Ready to map your fields?</h2>
          <p>Upload a satellite capture and see cropland and crop types on the live map in about a minute.</p>
          <div className="hero-actions">
            <Link to="/analyze" className="btn-primary btn-lg">Analyze Satellite Data</Link>
            <Link to="/signup" className="btn-secondary btn-lg btn-on-dark">Create Free Account</Link>
          </div>
        </section>
      </div>
    </div>
  );
}
