# Development Log Protocol

Create one log when a development branch starts:

```text
docs/development-logs/<branch-name-with-slash-replaced-by-hyphen>.md
```

Example:

```text
codex/bootstrap-adk-python
-> docs/development-logs/codex-bootstrap-adk-python.md
```

Use this template:

```markdown
# Branch Log: codex/example

## State

- Status: in_progress
- Started: YYYY-MM-DD HH:mm Asia/Shanghai
- Completed:
- Merged:
- Base commit:
- Final commit:

## Objective

One concrete branch objective.

## Scope

- Included:
- Excluded:

## Decisions

- Decision and short reason.

## Work Log

### YYYY-MM-DD HH:mm Asia/Shanghai

- Action:
- Result:
- Evidence:
- Decision:
- Next:

## Files Changed

- None yet.

## Tests And Checks

| Command | Result | Time |
| --- | --- | --- |
| Not run | Pending | |

## Known Limitations

- None currently known.

## Blockers

- None.

## Next Action

- Next concrete executable action.

## Completion Checklist

- [ ] Deliverables implemented
- [ ] Focused tests pass
- [ ] Full applicable test suite passes
- [ ] `git diff --check` passes
- [ ] Documentation updated
- [ ] Known limitations recorded
- [ ] `development-status.md` updated
```

Rules:

- Append timestamped work entries; do not rewrite history to make progress appear cleaner.
- Correct factual mistakes explicitly in a later entry.
- Record concise evidence such as commands, test counts, commit IDs, and file paths.
- Never record API keys, secrets, or sensitive requirement content.
- Update `docs/development-status.md` at the same milestones.
