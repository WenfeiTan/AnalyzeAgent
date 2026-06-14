# Branch Log: codex/workflow-stage-events

## State

- Status: merged
- Started: 2026-06-14 12:34 Asia/Shanghai
- Completed: 2026-06-14 12:40 Asia/Shanghai
- Merged: 2026-06-14 12:41 Asia/Shanghai
- Base commit: `6e5c8b4`
- Final commit: branch `0b79545`; squash merge `37c0989`

## Objective

Emit real, typed and request-scoped progress events from Initial and Update
workflows without coupling the Agent to HTTP or UI code.

## Scope

- Included: stage contracts, sink port, tracker, workflow instrumentation,
  public facade injection and focused tests.
- Excluded: Web jobs, SSE transport and Frontend rendering.

## Decisions

- Event sinks are injected per invocation to preserve concurrent job isolation.
- Expected Retriever degradation completes the search stage and remains a
  response warning; it does not fail the whole workflow.
- Failure metadata contains only stage and exception type, never business text.

## Work Log

### 2026-06-14 12:34 Asia/Shanghai

- Action: Created the branch from the latest main and inspected workflow code.
- Result: Identified the exact stage boundaries in Initial, Pipeline and Update.
- Evidence: Base commit `6e5c8b4`.
- Decision: Keep Agent events transport-neutral and synchronous to consume.
- Next: Implement and test request-scoped stage tracking.

### 2026-06-14 12:39 Asia/Shanghai

- Action: Added typed events, tracker, facade injection and workflow stages.
- Result: Initial and Update focused tests pass with ordered events.
- Evidence: 6 focused tests and Ruff passed.
- Decision: Backend will later adapt the sync sink to its in-process event store.
- Next: Run the full regression.

### 2026-06-14 12:40 Asia/Shanghai

- Action: Ran the complete Agent, Backend and Frontend regression.
- Result: The branch meets all completion gates.
- Evidence: Agent 69 tests, Backend 3 tests and Frontend 1 test passed; lint,
  typecheck, build and diff checks passed.
- Decision: Preserve the existing Analyze response schema; events are a separate
  invocation-scoped channel.
- Next: Commit and squash merge into `main`.

### 2026-06-14 12:41 Asia/Shanghai

- Action: Squash merged the branch into `main`.
- Result: Development Plan 2.0 progress is 2/5.
- Evidence: `main@37c0989`.
- Decision: Use the event sink as the Backend job store input.
- Next: Create `codex/web-api-job-runtime`.

## Files Changed

- `agent/src/analyze_agent/workflow_events.py`
- Initial, Update, shared pipeline and public facade.
- Workflow event and Update sequence tests.

## Tests And Checks

| Command | Result | Time |
| --- | --- | --- |
| Focused workflow tests | 6 passed | 2026-06-14 12:39 |
| `make agent-lint` | Passed | 2026-06-14 12:39 |
| `git diff --check` | Passed | 2026-06-14 12:39 |
| `make test` | Passed (69 + 3 + 1) | 2026-06-14 12:40 |
| `make lint` | Passed | 2026-06-14 12:40 |
| `make frontend-build` | Passed | 2026-06-14 12:40 |

## Known Limitations

- Events are not transported over SSE until the Backend job branch.
- Active event buffers are not persisted.

## Blockers

- None.

## Next Action

- Start `codex/web-api-job-runtime`.

## Completion Checklist

- [x] Deliverables implemented
- [x] Focused tests pass
- [x] Full applicable test suite passes
- [x] `git diff --check` passes
- [x] Documentation updated
- [x] Known limitations recorded
- [x] `development-status.md` updated
