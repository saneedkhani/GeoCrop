import { useEffect, useState } from "react";
import { AnalyzeForm } from "../pages/Analyze";
import { JobProgress, jobTitle, useJob } from "../pages/Processing";
import Icon from "./Icon";

type Props = {
  open: boolean;
  onClose: () => void;
  /** A job was started (upload or re-analysis). */
  onStarted?: (jobId: string) => void;
  /** "View on Live Map" after the job: close the pop-up and show the new results. */
  onViewResults: () => void;
};

/** Analyze Imagery as a pop-up over the Live Map. Same form and progress view as the pages.
 *  Closing only hides it, so an upload or a running job keeps its state. */
export default function AnalyzeModal({ open, onClose, onStarted, onViewResults }: Props) {
  const [jobId, setJobId] = useState<string | null>(null);
  const { data: job } = useJob(jobId ?? undefined);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <div className="modal-backdrop" hidden={!open} onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="analyze-title">
        <div className="modal-head">
          <span className="icon-tile"><Icon name={jobId ? "activity" : "upload"} size={20} /></span>
          <div>
            <h2 id="analyze-title">{jobId ? jobTitle(job) : "Process Satellite Data"}</h2>
            <p className="small muted">
              {jobId ? job?.message ?? "Preparing…"
                : "Upload raw Sentinel-2 imagery to map cropland and classify crops. Results appear on the live map as soon as each model finishes."}
            </p>
          </div>
          <button className="modal-close" aria-label="Close" onClick={onClose}><Icon name="x" size={18} /></button>
        </div>
        <div className="modal-body">
          {jobId ? (
            <JobProgress jobId={jobId} actions={<>
              <button className="btn-primary" onClick={() => { setJobId(null); onViewResults(); }}>View on Live Map</button>
              <button className="btn-secondary" onClick={() => setJobId(null)}>Analyze another image</button>
            </>} />
          ) : (
            <AnalyzeForm onStarted={(id) => { setJobId(id); onStarted?.(id); }} />
          )}
        </div>
      </div>
    </div>
  );
}
