# Branch Log: codex/observability-hardening

## State

- Status: completed
- Started: 2026-06-14 00:56 Asia/Shanghai
- Completed: 2026-06-14 01:03 Asia/Shanghai
- Merged: 2026-06-14 01:04 Asia/Shanghai
- Base commit: `eb0d68a`
- Final commit: `074e725`

## Objective

Add production-oriented observability, bounded resilience, redaction, and security safeguards.

## Scope

- Included: JSON logs, correlation context, metrics, timeout/retry wrappers, bounded schema repair, secret redaction, prompt-injection warnings, configuration, regression tests, and runbook updates.
- Excluded: External telemetry backend, real MCP integration, deployment infrastructure, and live Gemini quality evaluation.

## Decisions

- Never log raw requirement, supplemental information, chunks, feedback reasons, or API keys.
- Use bounded attempts and timeouts; no unbounded model, retriever, or schema-repair loops.
- Warn on prompt-injection patterns while preserving the requirement for business analysis.
- Keep metrics process-local and document the future exporter boundary.
- Limit structured-output repair separately from external-call retry attempts.

## Work Log

### 2026-06-14 00:56 Asia/Shanghai

- Action: Created the hardening branch from `main`.
- Result: Branch starts at `eb0d68a`.
- Evidence: Git branch and HEAD checks.
- Decision: Implement infrastructure with standard-library primitives where practical.
- Next: Add observability, resilience, bounded repair, security checks, and tests.

### 2026-06-14 01:03 Asia/Shanghai

- Action: Added JSON logging, correlation context, redaction, metrics, retry/timeout wrappers, bounded schema repair, injection warnings, configuration, tests, and runbook.
- Result: External calls are bounded; secrets and raw business content are excluded from operational logs; degraded retrieval cannot create fake high-confidence mappings.
- Evidence: `make test` passed 66 tests; Ruff, env, smoke, and diff checks passed.
- Decision: Real telemetry export and vector-mcp transport remain deferred to deployment/integration work.
- Next: Commit and merge, then run final verification from clean `main`.

### 2026-06-14 01:04 Asia/Shanghai

- Action: Committed and squash-merged the branch into `main`.
- Result: Observability and hardening are available on `main`.
- Evidence: Main implementation commit `074e725`.
- Decision: Mark all currently applicable branches merged after final regression.
- Next: Run final verification and close the current development scope.

### 2026-06-14 01:06 Asia/Shanghai

- Action: Ran final verification from `main` after all implementation merges.
- Result: Dependency lock, package build/install, tests, lint, configuration, smoke, ADK declarations, and diff checks passed.
- Evidence: 66 tests passed; `uv sync --locked --offline` succeeded; all three ADK FunctionTool declarations generated.
- Decision: Current executable scope is complete; keep vector-mcp adapter deferred.
- Next: Await the real vector-mcp contract or new user direction.

## Files Changed

- `.env.example`
- `README.md`
- `docs/runbook.md`
- `src/analyze_agent/config.py`
- `src/analyze_agent/observability.py`
- `src/analyze_agent/resilience.py`
- `src/analyze_agent/security.py`
- `src/analyze_agent/runtime.py`
- `src/analyze_agent/tools.py`
- `src/analyze_agent/application/analysis_pipeline.py`
- `src/analyze_agent/adapters/gemini_structured.py`
- `src/analyze_agent/adapters/gemini_requirement_analyzer.py`
- `src/analyze_agent/adapters/gemini_requirement_updater.py`
- `src/analyze_agent/adapters/gemini_knowledge_reconstructor.py`
- `src/analyze_agent/adapters/resilient.py`
- `tests/adapters/test_gemini_requirement_analyzer.py`
- `tests/adapters/test_resilient.py`
- `tests/application/test_initial_analysis.py`
- `tests/test_config.py`
- `tests/test_observability.py`
- `tests/test_security.py`
- `docs/development-logs/codex-observability-hardening.md`
- `docs/development-status.md`

## Tests And Checks

| Command | Result | Time |
| --- | --- | --- |
| `make test` | Passed: 66 tests | 2026-06-14 01:03 |
| `make lint` | Passed | 2026-06-14 01:03 |
| Gemini placeholder env/smoke checks | Passed | 2026-06-14 01:03 |
| `git diff --check` | Passed | 2026-06-14 01:03 |

## Known Limitations

- Metrics remain process-local until a deployment telemetry backend is selected.

## Blockers

- None.

## Next Action

- Commit and merge this branch, then run final verification from `main`.

## Completion Checklist

- [x] Deliverables implemented
- [x] Focused tests pass
- [x] Full applicable test suite passes
- [x] `git diff --check` passes
- [x] Documentation updated
- [x] Known limitations recorded
- [x] `development-status.md` updated
