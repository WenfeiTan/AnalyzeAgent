# Branch Log: codex/web-api-job-runtime

## State

- Status: completed
- Started: 2026-06-14 12:42 Asia/Shanghai
- Completed: 2026-06-14 12:50 Asia/Shanghai
- Merged:
- Base commit: `320590a`
- Final commit:

## Objective

Expose versioned Initial, Update, job, SSE and requirement-history APIs without
leaking Agent internals into the Backend.

## Scope

- Included: `/api/v1` contracts, in-process jobs, bounded events, SSE replay,
  CORS, error mapping, history reads and per-job Fake KB scenarios.
- Excluded: React UI, production job persistence and real vector-mcp.

## Decisions

- Create an isolated Agent facade per job through a public demo factory.
- Keep active jobs and stage events process-local with bounded retention.
- Use a stable error envelope instead of FastAPI's default validation payload.
- Expose requirement history through `AnalyzeAgentHistory`, not direct Backend
  SQLite access.

## Work Log

### 2026-06-14 12:42 Asia/Shanghai

- Action: Started the branch and inspected repository/history boundaries.
- Result: Identified missing public history listing and demo scenario factory.
- Evidence: Base commit `320590a`.
- Decision: Extend the Agent public facade before adding HTTP routes.
- Next: Implement public history/demo capabilities and the job API.

### 2026-06-14 12:49 Asia/Shanghai

- Action: Implemented versioned jobs, SSE, history, CORS and stable errors.
- Result: Backend focused API tests pass with injected fake agents.
- Evidence: Backend 9 tests passed; Agent regression passed before the final
  demo-factory test was added.
- Decision: Event replay ends with a terminal `job` SSE event.
- Next: Run focused demo and complete aggregate regressions.

### 2026-06-14 12:50 Asia/Shanghai

- Action: Ran all workspace tests, lint, typecheck and production build.
- Result: The API branch meets all completion gates.
- Evidence: Agent 70 tests, Backend 9 tests and Frontend 1 test passed.
- Decision: Keep the Backend process-local job store explicit in configuration
  and documentation rather than implying durable execution.
- Next: Commit and squash merge into `main`.

## Files Changed

- Agent public history summary, history facade and demo agent factory.
- Backend configuration, HTTP models, job store/service and FastAPI routes.
- API, concurrency, SSE, error and history tests.

## Tests And Checks

| Command | Result | Time |
| --- | --- | --- |
| `make backend-test` | 9 passed | 2026-06-14 12:48 |
| `make backend-lint` | Passed | 2026-06-14 12:48 |
| `make agent-test` | 69 passed before final test | 2026-06-14 12:48 |
| `git diff --check` | Passed | 2026-06-14 12:48 |
| `make test` | Passed (70 + 9 + 1) | 2026-06-14 12:50 |
| `make lint` | Passed | 2026-06-14 12:50 |
| `make frontend-build` | Passed | 2026-06-14 12:50 |

## Known Limitations

- Jobs and event buffers are lost when the Backend process restarts.
- Fake scenario payloads are code-owned placeholders pending final demo resource
  hardening.
- Real vector-mcp remains deferred.

## Blockers

- None.

## Next Action

- Commit and squash merge into `main`.

## Completion Checklist

- [x] Deliverables implemented
- [x] Focused tests pass
- [x] Full applicable test suite passes
- [x] `git diff --check` passes
- [x] Documentation updated
- [x] Known limitations recorded
- [x] `development-status.md` updated
