import { fireEvent, render, screen } from "@testing-library/react";

import type { JobResponse } from "../src/api/types";
import { ResultView } from "../src/components/ResultView";

const job = {
  job_id: "0467c989-30f9-442b-8030-e7f9fda7ca19",
  request_id: "9f5b9de4-f68e-4fee-a776-b46e1f34b054",
  status: "completed",
  created_at: "2026-06-14T00:00:00Z",
  updated_at: "2026-06-14T00:00:01Z",
  request_payload: { requirement: "Build an ADC review GDA." },
  result: {
    schema_version: "1.0",
    request_id: "9f5b9de4-f68e-4fee-a776-b46e1f34b054",
    requirement_id: "6c3348ba-bbe2-4df7-a42c-76e4862b61de",
    revision_id: "b4bd8bfb-17ef-44bc-8595-2be40e68fc5e",
    analyzed_requirement: {
      summary: "Build an ADC review GDA.",
      business_goal: "Support the ADC review.",
      domain_context: ["ADC"],
      target_output: "GDA",
      constraints: [],
      negative_constraints: [],
    },
    clear_fields: [
      {
        suggestion_id: "55d6654f-1a93-4350-a01d-eb73450236bc",
        name: "Facility_id",
        confidence: { level: "high", score: 0.9 },
        origin: "explicit_requirement",
        priority: 1,
        search_strategy: "exact_field_first",
        normalized_terms: ["facility_id"],
        source_hints: [],
        evidence: [],
        rationale: "Explicit field.",
      },
    ],
    keywords: [],
    reused_mappings: [],
    warnings: [],
    trace: {
      prompt_version: "test-v1",
      model: "gemini-test",
      knowledge_base_queries: [],
      processing_time_ms: 12,
    },
  },
} satisfies JobResponse;

test("renders summarized results and expandable debug payload", () => {
  render(<ResultView job={job} />);

  expect(screen.getByText("Facility_id")).toBeVisible();
  expect(screen.getByText("high · 90%")).toBeVisible();

  fireEvent.click(screen.getByText("Debug payload"));
  expect(
    screen.getAllByText(/"prompt_version": "test-v1"/),
  ).toHaveLength(2);
});
