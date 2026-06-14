import { render, screen } from "@testing-library/react";

import { App } from "../src/App";

test("renders the independent frontend shell", () => {
  render(<App />);

  expect(screen.getByRole("heading", { name: "Analyze Agent" })).toBeVisible();
  expect(screen.getByText("Frontend workspace healthy")).toBeVisible();
});
