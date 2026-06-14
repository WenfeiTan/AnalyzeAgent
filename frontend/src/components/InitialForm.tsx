import { useState } from "react";

import type {
  DemoScenario,
  InitialJobRequest,
} from "../api/types";
import { ScenarioSelect } from "./ScenarioSelect";

export function InitialForm({
  scenarios,
  running,
  unavailable,
  onSubmit,
}: {
  scenarios: DemoScenario[];
  running: boolean;
  unavailable: boolean;
  onSubmit: (payload: InitialJobRequest) => Promise<void>;
}) {
  const [requirement, setRequirement] = useState(
    "Because the Basel 3 protocol changed, update the ADC review and build a GDA using Facility_id and ADC_entity_country.",
  );
  const [businessDomain, setBusinessDomain] = useState("ADC review");
  const [targetGda, setTargetGda] = useState("Basel 3 ADC review GDA");
  const [scenario, setScenario] = useState<DemoScenario>("empty");

  return (
    <form
      className="workflow-form"
      onSubmit={(event) => {
        event.preventDefault();
        void onSubmit({
          requirement,
          business_domain: businessDomain || null,
          target_gda: targetGda || null,
          knowledge_base_scenario: scenario,
        });
      }}
    >
      <div className="section-heading">
        <div>
          <p className="kicker">Initial workflow</p>
          <h2>Analyze a requirement</h2>
        </div>
        <span className="step-number">01</span>
      </div>
      <label className="field">
        <span>English requirement</span>
        <textarea
          required
          rows={7}
          value={requirement}
          onChange={(event) => setRequirement(event.target.value)}
        />
      </label>
      <div className="form-grid">
        <label className="field">
          <span>Business domain</span>
          <input
            value={businessDomain}
            onChange={(event) => setBusinessDomain(event.target.value)}
          />
        </label>
        <label className="field">
          <span>Target GDA</span>
          <input
            value={targetGda}
            onChange={(event) => setTargetGda(event.target.value)}
          />
        </label>
      </div>
      <ScenarioSelect
        value={scenario}
        scenarios={scenarios}
        onChange={setScenario}
      />
      <button
        className="primary-button"
        disabled={running || unavailable}
        type="submit"
      >
        {running
          ? "Analysis running..."
          : unavailable
            ? "Configure Gemini API key"
            : "Run initial analysis"}
      </button>
    </form>
  );
}
