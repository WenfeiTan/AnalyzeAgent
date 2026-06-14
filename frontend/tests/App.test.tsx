import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, vi } from "vitest";

import { App } from "../src/App";

const requirementId = "6c3348ba-bbe2-4df7-a42c-76e4862b61de";

afterEach(() => {
  vi.restoreAllMocks();
});

function mockBackend() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/api/v1/configuration")) {
        return Response.json({
          api_key_configured: true,
          model: "gemini-test",
          knowledge_base_provider: "fake",
          scenarios: ["empty", "complete_mapping"],
        });
      }
      if (url.endsWith("/api/v1/requirements")) {
        return Response.json([
          {
            requirement_id: requirementId,
            latest_revision_number: 2,
            summary: "Build an ADC review GDA.",
            created_at: "2026-06-14T00:00:00Z",
            updated_at: "2026-06-14T01:00:00Z",
          },
        ]);
      }
      if (url.endsWith(`/requirements/${requirementId}/revisions`)) {
        return Response.json([]);
      }
      throw new Error(`Unexpected request: ${url}`);
    }),
  );
}

test("renders configuration and navigates all demo workflows", async () => {
  mockBackend();
  render(<App />);

  expect(
    screen.getByRole("heading", {
      name: "Turn requirements into search-ready guidance.",
    }),
  ).toBeVisible();
  expect(screen.getByText("Fake Knowledge Base")).toBeVisible();
  await screen.findByText("gemini-test ready");
  expect(
    screen.getByRole("button", { name: "Run initial analysis" }),
  ).toBeEnabled();

  fireEvent.click(screen.getByRole("button", { name: "Update requirement" }));
  expect(
    screen.getByRole("heading", { name: "Refine an existing requirement" }),
  ).toBeVisible();
  expect(
    screen.getByRole("option", { name: /Rev 2 · Build an ADC review GDA/ }),
  ).toBeVisible();

  fireEvent.click(screen.getByRole("button", { name: "History" }));
  expect(
    screen.getByRole("heading", { name: "Requirement revisions" }),
  ).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: /Revision 2/ }));

  await waitFor(() =>
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining(`/requirements/${requirementId}/revisions`),
      expect.anything(),
    ),
  );
});
