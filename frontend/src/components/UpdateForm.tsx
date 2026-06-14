import { useState } from "react";

import type {
  DemoScenario,
  RequirementSummary,
  SearchFeedback,
  UpdateJobRequest,
} from "../api/types";
import { ScenarioSelect } from "./ScenarioSelect";

const EMPTY_FEEDBACK: SearchFeedback = {
  candidate_id: "",
  target_type: "field_mapping",
  decision: "reject",
  field_name: "",
  reason: "",
  asset: { asset_name: "" },
  attribute: { attribute_name: "" },
};

export function UpdateForm({
  requirements,
  scenarios,
  running,
  unavailable,
  onSubmit,
}: {
  requirements: RequirementSummary[];
  scenarios: DemoScenario[];
  running: boolean;
  unavailable: boolean;
  onSubmit: (payload: UpdateJobRequest) => Promise<void>;
}) {
  const [requirementId, setRequirementId] = useState("");
  const [supplement, setSupplement] = useState("");
  const [scenario, setScenario] = useState<DemoScenario>("empty");
  const [feedback, setFeedback] = useState<SearchFeedback[]>([]);

  const updateFeedback = (
    index: number,
    patch: Partial<SearchFeedback>,
  ) => {
    setFeedback((items) =>
      items.map((item, itemIndex) =>
        itemIndex === index ? { ...item, ...patch } : item,
      ),
    );
  };

  return (
    <form
      className="workflow-form"
      onSubmit={(event) => {
        event.preventDefault();
        void onSubmit({
          requirement_id: requirementId,
          supplemental_information: supplement || null,
          search_feedback: feedback,
          knowledge_base_scenario: scenario,
        });
      }}
    >
      <div className="section-heading">
        <div>
          <p className="kicker">Updated workflow</p>
          <h2>Refine an existing requirement</h2>
        </div>
        <span className="step-number">02</span>
      </div>
      <label className="field">
        <span>Requirement history</span>
        <select
          required
          value={requirementId}
          onChange={(event) => setRequirementId(event.target.value)}
        >
          <option value="">Select a stored requirement</option>
          {requirements.map((item) => (
            <option key={item.requirement_id} value={item.requirement_id}>
              Rev {item.latest_revision_number} · {item.summary.slice(0, 72)}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        <span>Supplemental information</span>
        <textarea
          rows={4}
          placeholder="Explain what changed or what the search results missed."
          value={supplement}
          onChange={(event) => setSupplement(event.target.value)}
        />
      </label>
      <div className="feedback-header">
        <div>
          <strong>Structured search feedback</strong>
          <small>Optional accept/reject signals from Asset Discovery.</small>
        </div>
        <button
          className="secondary-button"
          type="button"
          onClick={() =>
            setFeedback((items) => [
              ...items,
              structuredClone(EMPTY_FEEDBACK),
            ])
          }
        >
          Add feedback
        </button>
      </div>
      {feedback.map((item, index) => (
        <div className="feedback-card" key={`feedback-${index}`}>
          <div className="form-grid compact">
            <label className="field">
              <span>Target</span>
              <select
                value={item.target_type}
                onChange={(event) =>
                  updateFeedback(index, {
                    target_type: event.target
                      .value as SearchFeedback["target_type"],
                  })
                }
              >
                <option value="field_mapping">Field mapping</option>
                <option value="asset">Asset</option>
                <option value="attribute">Attribute</option>
              </select>
            </label>
            <label className="field">
              <span>Decision</span>
              <select
                value={item.decision}
                onChange={(event) =>
                  updateFeedback(index, {
                    decision: event.target
                      .value as SearchFeedback["decision"],
                  })
                }
              >
                <option value="reject">Reject</option>
                <option value="accept">Accept</option>
              </select>
            </label>
          </div>
          <div className="form-grid compact">
            <label className="field">
              <span>Candidate ID</span>
              <input
                required
                value={item.candidate_id}
                onChange={(event) =>
                  updateFeedback(index, { candidate_id: event.target.value })
                }
              />
            </label>
            <label className="field">
              <span>Field name</span>
              <input
                value={item.field_name ?? ""}
                onChange={(event) =>
                  updateFeedback(index, { field_name: event.target.value })
                }
              />
            </label>
          </div>
          <div className="form-grid compact">
            <label className="field">
              <span>Asset name</span>
              <input
                value={item.asset?.asset_name ?? ""}
                onChange={(event) =>
                  updateFeedback(index, {
                    asset: { asset_name: event.target.value },
                  })
                }
              />
            </label>
            <label className="field">
              <span>Attribute name</span>
              <input
                value={item.attribute?.attribute_name ?? ""}
                onChange={(event) =>
                  updateFeedback(index, {
                    attribute: { attribute_name: event.target.value },
                  })
                }
              />
            </label>
          </div>
          <label className="field">
            <span>Reason</span>
            <input
              value={item.reason ?? ""}
              onChange={(event) =>
                updateFeedback(index, { reason: event.target.value })
              }
            />
          </label>
          <button
            className="text-button danger"
            type="button"
            onClick={() =>
              setFeedback((items) =>
                items.filter((_, itemIndex) => itemIndex !== index),
              )
            }
          >
            Remove feedback
          </button>
        </div>
      ))}
      <ScenarioSelect
        value={scenario}
        scenarios={scenarios}
        onChange={setScenario}
      />
      <button
        className="primary-button"
        disabled={
          running ||
          unavailable ||
          !requirementId ||
          (!supplement && feedback.length === 0)
        }
        type="submit"
      >
        {running
          ? "Update running..."
          : unavailable
            ? "Configure Gemini API key"
            : "Run updated analysis"}
      </button>
    </form>
  );
}
