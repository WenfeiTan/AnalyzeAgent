import type { DemoScenario } from "../api/types";

const LABELS: Record<DemoScenario, string> = {
  empty: "Empty retrieval",
  complete_mapping: "Complete mapping",
  partial_mapping: "Partial mapping",
  no_evidence: "No valid evidence",
  timeout: "Timeout degradation",
  invalid: "Invalid response degradation",
};

export function ScenarioSelect({
  value,
  scenarios,
  onChange,
}: {
  value: DemoScenario;
  scenarios: DemoScenario[];
  onChange: (value: DemoScenario) => void;
}) {
  return (
    <label className="field">
      <span>Fake Knowledge Base scenario</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value as DemoScenario)}
      >
        {scenarios.map((scenario) => (
          <option key={scenario} value={scenario}>
            {LABELS[scenario]}
          </option>
        ))}
      </select>
      <small>Demo data only. No vector-mcp request is made.</small>
    </label>
  );
}
