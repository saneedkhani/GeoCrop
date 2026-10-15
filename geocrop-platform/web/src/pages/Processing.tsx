import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type Job } from "../api/client";
import Icon from "../components/Icon";

const label: Record<string, string> = { queued: "Queued", running: "Processing", done: "Complete", failed: "Failed" };

export default function Processing() {
  const { jobId } = useParams();
  const qc = useQueryClient();
  const { data: job, error } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api<Job>(`/jobs/${jobId}`),
    refetchInterval: (q) => (q.state.data && ["done", "failed"].includes(q.state.data.status) ? false : 1500),
  });

  useEffect(() => {
    if (job?.status === "done") {
      ["layers", "sources", "aois", "fields", "stats"].forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
    }
  }, [job?.status, qc]);

  const tone = job?.status === "done" ? "" : job?.status === "failed" ? "danger" : "warn";

  return (
    <div className="page-center">
      <span className="icon-tile"><Icon name="activity" size={22} /></span>
      <h1>{job?.status === "done" ? "Analysis complete" : job?.status === "failed" ? "Analysis stopped" : "Analysing your imagery"}</h1>
      <p>{job?.message ?? "Preparing…"}</p>

      <div className="card upload-card">
        {error && <div className="alert error">{(error as Error).message}</div>}
        {job && (
          <>
            <div className="sub-panel-head">
              <span className={`badge ${tone}`}>{label[job.status] ?? job.status}</span>
              <span className="small faint">{Math.round(job.progress * 100)}%</span>
            </div>
            <div className="progress"><div style={{ width: `${job.progress * 100}%` }} /></div>
            <ol className="steps-list">
              {job.steps.map((s) => (
                <li key={s.name} className={`step-row ${s.status}`}>
                  <span className="step-icon">{s.status === "done" ? <Icon name="check" size={13} /> : s.status === "failed" ? <Icon name="x" size={13} /> : null}</span>
                  {s.name}
                  <span className="state">{s.status}</span>
                </li>
              ))}
            </ol>
            {job.error && <div className="alert error">{job.error}</div>}
            <div className="two-inputs">
              <Link to="/map" className="btn-primary">View on Live Map</Link>
              <Link to="/analyze" className="btn-secondary">Analyze another image</Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
