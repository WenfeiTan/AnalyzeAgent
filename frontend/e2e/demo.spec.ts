import { expect, test, type Page } from "@playwright/test";

const requirementId = "11111111-1111-4111-8111-111111111111";
const revisionId = "22222222-2222-4222-8222-222222222222";
const requestId = "33333333-3333-4333-8333-333333333333";
const jobId = "44444444-4444-4444-8444-444444444444";

const result = {
  schema_version: "1.0",
  request_id: requestId,
  requirement_id: requirementId,
  revision_id: revisionId,
  analyzed_requirement: {
    summary: "Build a Basel 3 ADC review GDA.",
    business_goal: "Support the updated ADC review.",
    domain_context: ["ADC", "Basel 3"],
    target_output: "GDA",
    constraints: [],
    negative_constraints: [],
  },
  clear_fields: [
    {
      suggestion_id: "55555555-5555-4555-8555-555555555555",
      name: "Facility_id",
      confidence: { level: "medium", score: 0.7 },
      origin: "explicit_requirement",
      priority: 1,
      search_strategy: "exact_field_first",
      normalized_terms: ["facility_id"],
      source_hints: [],
      evidence: [],
      rationale: "Field name is explicitly stated in the requirement.",
    },
  ],
  keywords: [
    {
      suggestion_id: "66666666-6666-4666-8666-666666666666",
      name: "ADC",
      confidence: { level: "medium", score: 0.65 },
      origin: "requirement_analysis",
      priority: 2,
      search_strategy: "semantic_keyword",
      normalized_terms: ["ADC"],
      evidence: [],
      rationale: "Core review domain.",
    },
  ],
  reused_mappings: [],
  change_summary: null,
  warnings: [],
  trace: {
    prompt_version: "e2e-v1",
    model: "deterministic-e2e",
    knowledge_base_queries: ["Build a Basel 3 ADC review GDA."],
    processing_time_ms: 12,
  },
};

const completedJob = {
  job_id: jobId,
  request_id: requestId,
  status: "completed",
  created_at: "2026-06-14T00:00:00Z",
  updated_at: "2026-06-14T00:00:01Z",
  request_payload: {
    requirement: "Build a Basel 3 ADC review GDA.",
    knowledge_base_scenario: "empty",
  },
  result,
  error: null,
};

async function mockApi(page: Page) {
  await page.route("http://localhost:8000/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/v1/configuration") {
      await route.fulfill({
        json: {
          api_key_configured: true,
          model: "deterministic-e2e",
          knowledge_base_provider: "fake",
          scenarios: ["empty", "complete_mapping", "timeout"],
        },
      });
      return;
    }
    if (url.pathname === "/api/v1/requirements") {
      await route.fulfill({
        json: [
          {
            requirement_id: requirementId,
            latest_revision_number: 2,
            summary: "Build a Basel 3 ADC review GDA.",
            created_at: "2026-06-14T00:00:00Z",
            updated_at: "2026-06-14T00:00:01Z",
          },
        ],
      });
      return;
    }
    if (url.pathname.endsWith("/revisions")) {
      await route.fulfill({
        json: [
          {
            requirement_id: requirementId,
            revision_id: revisionId,
            revision_number: 2,
            full_requirement: "Build a Basel 3 ADC review GDA.",
            supplemental_information: "Include ADC entity country.",
            analyzed_requirement: result.analyzed_requirement,
            changes: [],
            feedback: [],
            output_snapshot: result,
            created_at: "2026-06-14T00:00:01Z",
          },
        ],
      });
      return;
    }
    if (
      url.pathname === "/api/v1/jobs/initial" ||
      url.pathname === "/api/v1/jobs/update"
    ) {
      await route.fulfill({
        status: 202,
        json: { job_id: jobId, request_id: requestId, status: "queued" },
      });
      return;
    }
    if (url.pathname.endsWith("/events")) {
      const stage = {
        job_id: jobId,
        request_id: requestId,
        stage: "completed",
        status: "completed",
        sequence: 1,
        timestamp: "2026-06-14T00:00:01Z",
        duration_ms: 12,
        metadata: {},
      };
      await route.fulfill({
        contentType: "text/event-stream",
        body: [
          "id: 1",
          "event: stage",
          `data: ${JSON.stringify(stage)}`,
          "",
          "id: 2",
          "event: job",
          `data: ${JSON.stringify(completedJob)}`,
          "",
          "",
        ].join("\n"),
      });
      return;
    }
    await route.fulfill({ status: 404, json: { error: "not mocked" } });
  });
}

test.beforeEach(async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await expect(page.getByText("deterministic-e2e ready")).toBeVisible();
});

test("runs initial analysis and exposes the debug payload", async ({ page }) => {
  await page.getByRole("button", { name: "Run initial analysis" }).click();

  await expect(
    page.getByRole("heading", {
      name: "Build a Basel 3 ADC review GDA.",
    }),
  ).toBeVisible();
  await expect(page.getByText("Facility_id", { exact: true })).toBeVisible();
  await expect(page.locator(".job-badge")).toHaveText("completed");

  await page.getByText("Debug payload").click();
  await expect(
    page.locator(".payload-grid > div").nth(2).locator("pre"),
  ).toBeVisible();
});

test("supports update feedback and stored revision inspection", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Update requirement" }).click();
  await page.getByLabel("Requirement history").selectOption(requirementId);
  await page.getByRole("button", { name: "Add feedback" }).click();
  await page.getByLabel("Candidate ID").fill("candidate-1");
  await page.getByLabel("Field name").fill("ADC_entity_country");
  await page.getByLabel("Asset name").fill("adc_entity");
  await page.getByLabel("Attribute name").fill("entity_country");
  await expect(
    page.getByRole("button", { name: "Run updated analysis" }),
  ).toBeEnabled();

  await page.getByRole("button", { name: "History" }).click();
  await page.getByRole("button", { name: /Revision 2/ }).click();
  await expect(page.getByText("Include ADC entity country.")).toBeVisible();
  await page.getByText("Stored output snapshot").click();
  await expect(page.getByText('"schema_version": "1.0"')).toBeVisible();
});
