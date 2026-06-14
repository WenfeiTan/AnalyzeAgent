import type { AnalyzeResult, JobResponse } from "../api/types";

function ConfidenceBadge({
  level,
  score,
}: {
  level: string;
  score: number;
}) {
  return (
    <span className={`confidence ${level}`}>
      {level} · {Math.round(score * 100)}%
    </span>
  );
}

export function ResultView({ job }: { job: JobResponse | null }) {
  if (!job?.result) {
    return null;
  }
  const result = job.result as AnalyzeResult;
  return (
    <section className="result-panel">
      <div className="section-heading">
        <div>
          <p className="kicker">Analyze result</p>
          <h2>{result.analyzed_requirement.summary}</h2>
        </div>
        <span className="revision-chip">
          {result.requirement_id.slice(0, 8)}
        </span>
      </div>
      <div className="goal-card">
        <span>Business goal</span>
        <strong>{result.analyzed_requirement.business_goal}</strong>
      </div>
      <div className="result-grid">
        <ResultGroup title="Clear fields" count={result.clear_fields?.length ?? 0}>
          {result.clear_fields?.map((field) => (
            <article className="suggestion-card" key={field.suggestion_id}>
              <div>
                <strong>{field.name}</strong>
                <small>Priority {field.priority} · exact field first</small>
              </div>
              <ConfidenceBadge {...field.confidence} />
              <p>{field.rationale}</p>
            </article>
          ))}
        </ResultGroup>
        <ResultGroup title="Keywords" count={result.keywords?.length ?? 0}>
          {result.keywords?.map((keyword) => (
            <article className="suggestion-card" key={keyword.suggestion_id}>
              <div>
                <strong>{keyword.name}</strong>
                <small>Priority {keyword.priority} · semantic keyword</small>
              </div>
              <ConfidenceBadge {...keyword.confidence} />
              <p>{keyword.rationale}</p>
            </article>
          ))}
        </ResultGroup>
      </div>
      <ResultGroup
        title="Reused mappings"
        count={result.reused_mappings?.length ?? 0}
      >
        {result.reused_mappings?.map((mapping) => (
          <article className="mapping-card" key={mapping.mapping_id}>
            <div>
              <strong>{mapping.field_name}</strong>
              <ConfidenceBadge {...mapping.confidence} />
            </div>
            {mapping.sources.map((source, index) => (
              <code key={`${mapping.mapping_id}-${index}`}>
                {source.asset.asset_name ?? source.asset.asset_id} →{" "}
                {source.attribute.attribute_name ?? source.attribute.attribute_id}
              </code>
            ))}
            <p>{mapping.rationale}</p>
          </article>
        ))}
      </ResultGroup>
      {(result.warnings?.length ?? 0) > 0 && (
        <div className="warning-box">
          <strong>Warnings</strong>
          {result.warnings?.map((warning) => (
            <span key={warning}>{warning}</span>
          ))}
        </div>
      )}
      <details className="debug-payload">
        <summary>Debug payload</summary>
        <div className="payload-grid">
          <div>
            <span>Request</span>
            <pre>{JSON.stringify(job.request_payload, null, 2)}</pre>
          </div>
          <div>
            <span>Response</span>
            <pre>{JSON.stringify(result, null, 2)}</pre>
          </div>
          <div>
            <span>Trace</span>
            <pre>{JSON.stringify(result.trace, null, 2)}</pre>
          </div>
        </div>
      </details>
    </section>
  );
}

function ResultGroup({
  title,
  count,
  children,
}: {
  title: string;
  count: number;
  children: React.ReactNode;
}) {
  return (
    <div className="result-group">
      <div className="group-title">
        <h3>{title}</h3>
        <span>{count}</span>
      </div>
      {count === 0 ? (
        <p className="muted">No suggestions in this group.</p>
      ) : (
        children
      )}
    </div>
  );
}
