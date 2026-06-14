import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { RequirementSummary, Revision } from "../api/types";

export function HistoryPanel({
  requirements,
}: {
  requirements: RequirementSummary[];
}) {
  const [selected, setSelected] = useState("");
  const [revisions, setRevisions] = useState<Revision[]>([]);

  useEffect(() => {
    if (!selected) {
      setRevisions([]);
      return;
    }
    void api.revisions(selected).then(setRevisions);
  }, [selected]);

  return (
    <section className="history-panel">
      <div className="section-heading">
        <div>
          <p className="kicker">SQLite history</p>
          <h2>Requirement revisions</h2>
        </div>
        <span className="step-number">{requirements.length}</span>
      </div>
      <div className="history-layout">
        <div className="history-list">
          {requirements.length === 0 && (
            <p className="muted">No completed requirements yet.</p>
          )}
          {requirements.map((item) => (
            <button
              className={selected === item.requirement_id ? "selected" : ""}
              key={item.requirement_id}
              type="button"
              onClick={() => setSelected(item.requirement_id)}
            >
              <strong>Revision {item.latest_revision_number}</strong>
              <span>{item.summary}</span>
              <small>{new Date(item.updated_at).toLocaleString()}</small>
            </button>
          ))}
        </div>
        <div className="revision-list">
          {revisions.map((revision) => (
            <article key={revision.revision_id}>
              <div>
                <strong>Revision {revision.revision_number}</strong>
                <small>{new Date(revision.created_at).toLocaleString()}</small>
              </div>
              <p>{revision.full_requirement}</p>
              {revision.supplemental_information && (
                <blockquote>{revision.supplemental_information}</blockquote>
              )}
              <details>
                <summary>Stored output snapshot</summary>
                <pre>
                  {JSON.stringify(revision.output_snapshot, null, 2)}
                </pre>
              </details>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
