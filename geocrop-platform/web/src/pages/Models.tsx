import { fmt } from "../api/client";
import { useModels } from "../api/hooks";
import Icon from "../components/Icon";

const status = { ready: ["Ready", ""], example: ["Index", "info"], stub: ["Coming soon", "warn"] } as const;

export default function Models() {
  const { data, isLoading } = useModels();

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Models</h1>
          <p>The analysis models available in GeoCrop. Each model plugs into the platform the same way, so new ones appear here and on the map without changes elsewhere.</p>
        </div>
      </div>
      {isLoading && <p className="muted">Loading…</p>}
      {data?.registry_errors?.length ? <div className="alert error">{data.registry_errors.join(" ")}</div> : null}

      <div className="model-grid">
        {data?.models.map((m) => {
          const [text, tone] = status[m.status] ?? [m.status, "neutral"];
          return (
            <article key={m.key} className="card model-card">
              <div className="card-head">
                <h3>{m.name}</h3>
                <span className={`badge ${tone}`}>{text}</span>
              </div>
              <div className="card-body">
                <dl className="kv">
                  <dt>Version</dt><dd>{m.version}</dd>
                  <dt>Needs</dt><dd>{m.requires.join(", ") || "–"}</dd>
                  <dt>Produces</dt><dd>{m.outputs.join(", ")}</dd>
                  {m.input_bands && (<><dt>Bands</dt><dd>{m.input_bands.join(", ")}</dd></>)}
                  <dt>Valid for</dt><dd>{m.valid_regions.join("; ") || "–"}</dd>
                  {m.last_run_metrics?.accuracy !== undefined && (
                    <>
                      <dt>Accuracy</dt>
                      <dd>
                        {fmt(m.last_run_metrics.accuracy! * 100, 1)}%
                        {m.last_run_metrics.macro_f1 !== undefined && <> · macro F1 {fmt(m.last_run_metrics.macro_f1!, 2)}</>}
                      </dd>
                    </>
                  )}
                </dl>
                {m.class_scores.length > 0 && (
                  <>
                    <p className="small faint" style={{ marginTop: "1rem", fontWeight: 700 }}>F1 score by class</p>
                    <ul className="score-list">
                      {m.class_scores.map((c) => (
                        <li key={c.label} className="score-row">
                          <span className="name" title={c.label}>{c.label}</span>
                          <span className="dist-track"><span className="dist-fill" style={{ display: "block", width: `${c.f1 * 100}%`, background: "var(--field)" }} /></span>
                          <span className="faint">{fmt(c.f1, 2)}</span>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
                {m.status === "stub" && <p className="small muted" style={{ marginTop: ".75rem" }}>This model is planned and will be available in a future release.</p>}
              </div>
            </article>
          );
        })}
      </div>

      <section className="card">
        <div className="card-head"><h3><Icon name="plug" size={18} /> Adding a model</h3></div>
        <div className="card-body">
          <ol className="ordered-steps">
            <li>Copy <code>backend/model_registry/builtin/example_ndvi</code> to a new folder.</li>
            <li>In <code>manifest.yaml</code>, set <code>key</code>, <code>name</code>, <code>requires</code> and <code>outputs</code>.</li>
            <li>Write <code>run()</code> in <code>task.py</code>: read the image, write a GeoTIFF, return it.</li>
            <li>Put trained weights in <code>data/models/</code> if the model needs them.</li>
            <li>Restart the <code>api</code> and <code>worker</code> services. The model appears here and in Analyze Imagery.</li>
          </ol>
        </div>
      </section>
    </div>
  );
}
