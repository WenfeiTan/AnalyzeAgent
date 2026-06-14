# Branch Log: codex/demo-hardening-runbook

## State

- Status: merged
- Started: 2026-06-14 13:12 Asia/Shanghai
- Completed: 2026-06-14 13:33 Asia/Shanghai
- Merged: 2026-06-14 13:35 Asia/Shanghai
- Base commit: `618cd03`
- Final commit: branch `8c48ea1`; squash merge `0b57b11`

## Objective

Make the local demo repeatable, observable and documented with deterministic
end-to-end regression coverage.

## Scope

- Included: package-owned Fake KB resources, API and browser E2E tests, unified
  development startup, cleanup instructions, Web logs/metrics and runbook.
- Excluded: production deployment, authentication and real vector-mcp.

## Decisions

- Keep real runtime submission gated by a Gemini API key.
- Use injected deterministic adapters for automated full-workflow tests.
- Store Fake KB demo payloads in the installable Agent package.

## Work Log

### 2026-06-14 13:12 Asia/Shanghai

- Action: Started the final Development Plan 2.0 branch and audited current
  resources, runtime composition, observability and documentation.
- Result: Identified hardcoded demo chunks, no unified dev command, and no Web
  job/stage metrics endpoint.
- Evidence: Base commit `618cd03`.
- Decision: Harden existing boundaries without introducing a no-key production
  execution mode.
- Next: Package demo resources and add deterministic API workflow tests.

### 2026-06-14 13:20 Asia/Shanghai

- Action: Packaged all Fake KB scenarios and added deterministic API workflow
  regression.
- Result: Initial empty/reuse, Update supplement/feedback and timeout
  degradation pass through the real API, Agent services and SQLite repository.
- Evidence: Agent 71 tests and Backend 15 tests passed at this milestone.
- Decision: Keep deterministic model adapters test-only; runtime remains Gemini
  key gated.
- Next: Add Web observability and local operations.

### 2026-06-14 13:27 Asia/Shanghai

- Action: Added Web job/stage metrics, safe JSON logs, unified startup, smoke
  checks and cleanup.
- Result: `make dev` starts both processes with one repository-local database;
  health/configuration/metrics smoke passes and `Ctrl-C` stops both processes.
- Evidence: Browser configuration view loaded from the unified command and
  ports 8000/5173 were released after shutdown.
- Decision: Expose process-local metrics at `/api/v1/metrics`.
- Next: Complete browser automation and full regression.

### 2026-06-14 13:33 Asia/Shanghai

- Action: Completed Playwright paths, runbook, wheel/resource verification and
  all final branch checks.
- Result: The final branch meets its implementation and documentation gates.
- Evidence: Agent 71, Backend 17, Frontend 2 and Playwright 2 tests passed;
  Ruff, ESLint, typecheck, production build, OpenAPI generation, env check,
  wheel build, smoke test and `git diff --check` passed.
- Decision: Keep production telemetry export and real vector-mcp outside this
  local prototype.
- Next: Commit and squash merge into `main`.

### 2026-06-14 13:35 Asia/Shanghai

- Action: Committed and squash merged the final branch.
- Result: Development Plan 2.0 progress is 5/5.
- Evidence: Branch `8c48ea1`; `main@0b57b11`.
- Decision: Run one final clean-main regression before closing the plan.
- Next: Verify clean `main`.

## Files Changed

- Packaged Agent demo resources and loader.
- Deterministic API workflow E2E tests.
- Backend Web logging, metrics and typed metrics endpoint.
- Unified dev/smoke/cleanup scripts and Make targets.
- Playwright browser paths, OpenAPI output and operational documentation.

## Tests And Checks

| Command | Result | Time |
| --- | --- | --- |
| `make agent-test` | 71 passed | 2026-06-14 13:31 |
| `make backend-test` | 17 passed | 2026-06-14 13:31 |
| `make frontend-test` | 2 passed | 2026-06-14 13:31 |
| `make frontend-e2e` | 2 passed | 2026-06-14 13:33 |
| `make lint` | Passed | 2026-06-14 13:32 |
| `make frontend-build` | Passed | 2026-06-14 13:32 |
| `make generate-api-types` | Passed | 2026-06-14 13:31 |
| `GOOGLE_API_KEY=test-placeholder make agent-env-check` | Passed | 2026-06-14 13:31 |
| `uv build` | Wheel includes all demo JSON | 2026-06-14 13:29 |
| `make dev` + `make smoke-test` | Passed | 2026-06-14 13:27 |
| `git diff --check` | Passed | 2026-06-14 13:33 |

## Known Limitations

- Real vector-mcp remains deferred until its external contract is available.

## Blockers

- None.

## Next Action

- Run final clean-main regression.

## Completion Checklist

- [x] Deliverables implemented
- [x] Focused tests pass
- [x] Full applicable test suite passes
- [x] `git diff --check` passes
- [x] Documentation updated
- [x] Known limitations recorded
- [x] `development-status.md` updated
