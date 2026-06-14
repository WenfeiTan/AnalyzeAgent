# Branch Log: codex/split-agent-backend-frontend

## State

- Status: completed
- Started: 2026-06-14 12:13 Asia/Shanghai
- Completed: 2026-06-14 12:32 Asia/Shanghai
- Merged:
- Base commit: `acdc65f`
- Final commit:

## Objective

Split the repository into a reusable Python Agent package, an independent
FastAPI Backend, and an independent React/TypeScript Frontend.

## Scope

- Included: workspace migration, Agent public facade, Backend import boundary,
  Frontend scaffold, root orchestration commands, tests and documentation.
- Excluded: workflow stage instrumentation, job/SSE API implementation, complete
  interactive UI, real vector-mcp integration.

## Decisions

- Keep Agent as an in-process Python package rather than a third network service.
- Enforce the dependency direction `frontend -> backend -> agent`.
- Backend may import only the Agent public facade.

## Work Log

### 2026-06-14 12:13 Asia/Shanghai

- Action: Verified the planning baseline and existing repository health.
- Result: Started the first Development Plan 2.0 branch.
- Evidence: 66 pytest tests passed; Ruff and `git diff --check` passed; Node
  `22.17.0` and npm `10.9.2` are available.
- Decision: Preserve existing behavior during the workspace migration.
- Next: Move the Python project to `agent/` and scaffold Backend and Frontend.

### 2026-06-14 12:32 Asia/Shanghai

- Action: Completed the workspace split, public facade, dependency locks and
  aggregate regression.
- Result: Agent, Backend and Frontend are independently installable and tested.
- Evidence: Agent 67 tests, Backend 3 tests and Frontend 1 test passed; all
  lint/typecheck/build and diff checks passed.
- Decision: Use pnpm instead of npm because npm stalled repeatedly in this
  environment; `pnpm-lock.yaml` is the reproducible Frontend lock.
- Next: Commit and squash merge the branch into `main`.

## Files Changed

- Moved the existing Python project into `agent/`.
- Added the `AnalyzeAgent` public facade and history access.
- Added an independent FastAPI Backend shell and architecture tests.
- Added an independent React/Vite/TypeScript Frontend shell.
- Added workspace-specific lockfiles and root orchestration commands.
- Updated README, runbook, environment example, ignore rules, plan and status.

## Tests And Checks

| Command | Result | Time |
| --- | --- | --- |
| `make test` | 66 passed | 2026-06-14 12:13 |
| `make lint` | Passed | 2026-06-14 12:13 |
| `git diff --check` | Passed | 2026-06-14 12:13 |
| `make agent-test` | 67 passed | 2026-06-14 12:31 |
| `make agent-lint` | Passed | 2026-06-14 12:31 |
| `make backend-test` | 3 passed | 2026-06-14 12:31 |
| `make frontend-typecheck` | Passed | 2026-06-14 12:31 |
| `make frontend-test` | 1 passed | 2026-06-14 12:31 |
| `make frontend-build` | Passed | 2026-06-14 12:31 |
| `make frontend-lint` | Passed | 2026-06-14 12:31 |
| `make test` | Passed (67 + 3 + 1) | 2026-06-14 12:32 |
| `make lint` | Passed | 2026-06-14 12:32 |
| `make frontend-build` | Passed | 2026-06-14 12:32 |
| Backend `uv sync --locked --offline` | Passed | 2026-06-14 12:32 |
| `git diff --check` | Passed | 2026-06-14 12:32 |

## Known Limitations

- Backend API and interactive UI remain for later branches.
- Agent and FastAPI currently emit upstream deprecation warnings in tests.

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
