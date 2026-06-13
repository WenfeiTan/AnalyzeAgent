# Branch Log: codex/domain-contracts

## State

- Status: completed
- Started: 2026-06-14 00:09 Asia/Shanghai
- Completed: 2026-06-14 00:13 Asia/Shanghai
- Merged: 2026-06-14 00:14 Asia/Shanghai
- Base commit: `f6d7333`
- Final commit: `a6958cd`

## Objective

Define strict first-version domain contracts and deterministic confidence rules.

## Scope

- Included: Request/response schemas, feedback and mapping models, normalized chunks, error contracts, confidence levels, scoring rules, and unit tests.
- Excluded: SQLite persistence, Gemini workflow calls, retriever implementations, and ADK orchestration.

## Decisions

- Use Pydantic v2 models with `extra="forbid"` at external boundaries.
- Separate model-generated analysis signals from code-generated confidence and identifiers.
- Keep all confidence weights in a typed configuration object.
- Treat user rejection as exclusion (`None`) instead of a zero-confidence suggestion.
- Require complete field/attribute/asset identity for field-mapping feedback.

## Work Log

### 2026-06-14 00:09 Asia/Shanghai

- Action: Created the domain contracts branch from `main`.
- Result: Branch starts at `f6d7333` with bootstrap checks passing.
- Evidence: `git status --short --branch`.
- Decision: Build contracts before persistence and workflows.
- Next: Implement typed models and confidence rules with focused tests.

### 2026-06-14 00:13 Asia/Shanghai

- Action: Implemented Pydantic request/response, feedback, mapping, chunk, error, and model-signal contracts plus deterministic confidence scoring.
- Result: Contracts reject unknown external fields and incomplete feedback; confidence baselines and penalties are covered by tests.
- Evidence: `make test` passed 18 tests; `make lint` and `git diff --check` passed; main schemas generate JSON Schema.
- Decision: Keep generated IDs, priorities, and final confidence outside Gemini signal models.
- Next: Commit and squash-merge the branch, then start SQLite revisions.

### 2026-06-14 00:14 Asia/Shanghai

- Action: Committed and squash-merged the branch into `main`.
- Result: Domain contracts and confidence rules are available on `main`.
- Evidence: Main commit `a6958cd`.
- Decision: Continue with code-managed SQLite revisions.
- Next: Create `codex/sqlite-revisions`.

## Files Changed

- `pyproject.toml`
- `uv.lock`
- `src/analyze_agent/domain/__init__.py`
- `src/analyze_agent/domain/confidence.py`
- `src/analyze_agent/domain/errors.py`
- `src/analyze_agent/domain/models.py`
- `tests/domain/test_confidence.py`
- `tests/domain/test_models.py`
- `docs/development-logs/codex-domain-contracts.md`
- `docs/development-status.md`

## Tests And Checks

| Command | Result | Time |
| --- | --- | --- |
| `make test` | Passed: 18 tests | 2026-06-14 00:13 |
| `make lint` | Passed | 2026-06-14 00:13 |
| `git diff --check` | Passed | 2026-06-14 00:13 |
| JSON Schema smoke check | Passed for initial, updated, and response contracts | 2026-06-14 00:13 |

## Known Limitations

- ES Agent's final contract may require a later versioned schema update.

## Blockers

- None.

## Next Action

- Commit and merge this branch, then create `codex/sqlite-revisions`.

## Completion Checklist

- [x] Deliverables implemented
- [x] Focused tests pass
- [x] Full applicable test suite passes
- [x] `git diff --check` passes
- [x] Documentation updated
- [x] Known limitations recorded
- [x] `development-status.md` updated
