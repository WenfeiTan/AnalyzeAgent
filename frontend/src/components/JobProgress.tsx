import type { JobResponse, StageEvent } from "../api/types";

const STAGE_LABELS: Record<string, string> = {
  validating_input: "Validating input",
  loading_revision: "Loading existing revision",
  updating_requirement: "Updating requirement",
  analyzing_requirement: "Analyzing requirement",
  searching_knowledge_base: "Reusing Knowledge Base",
  reconstructing_mappings: "Reconstructing mappings",
  calculating_confidence: "Calculating confidence",
  persisting_revision: "Persisting revision",
  completed: "Completed",
  failed: "Failed",
};

export function JobProgress({
  job,
  events,
}: {
  job: JobResponse | null;
  events: StageEvent[];
}) {
  if (!job && events.length === 0) {
    return (
      <section className="empty-state">
        <span className="pulse-dot" />
        <h3>Ready for a workflow</h3>
        <p>Submit an Initial or Updated requirement to inspect live stages.</p>
      </section>
    );
  }
  const latest = events.at(-1);
  return (
    <section className="progress-panel" aria-live="polite">
      <div className="section-heading">
        <div>
          <p className="kicker">Working status</p>
          <h2>{latest ? STAGE_LABELS[latest.stage] : "Job queued"}</h2>
        </div>
        <span className={`job-badge ${job?.status ?? "running"}`}>
          {job?.status ?? "running"}
        </span>
      </div>
      <ol className="timeline">
        {events.map((event) => (
          <li
            className={`timeline-item ${event.status}`}
            key={`${event.sequence}-${event.status}`}
          >
            <span className="timeline-marker" />
            <div>
              <strong>{STAGE_LABELS[event.stage]}</strong>
              <small>
                {event.status}
                {event.duration_ms != null
                  ? ` · ${Math.round(event.duration_ms)} ms`
                  : ""}
              </small>
            </div>
          </li>
        ))}
      </ol>
      {job?.error && (
        <div className="error-message">
          <strong>{job.error.code}</strong>
          <span>{job.error.message}</span>
        </div>
      )}
    </section>
  );
}
