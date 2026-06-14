.PHONY: agent-env-check agent-lint agent-run agent-test backend-lint backend-run \
	backend-test frontend-build frontend-dev frontend-lint frontend-test \
	frontend-typecheck lint test

agent-env-check:
	cd agent && .venv/bin/python -m analyze_agent

agent-run:
	cd agent && .venv/bin/adk run src/analyze_agent

agent-test:
	cd agent && .venv/bin/pytest

agent-lint:
	cd agent && .venv/bin/ruff check .

backend-run:
	cd backend && .venv/bin/uvicorn analyze_api.app:app --reload

backend-test:
	cd backend && .venv/bin/pytest

backend-lint:
	cd backend && .venv/bin/ruff check .

frontend-dev:
	cd frontend && pnpm dev

frontend-test:
	cd frontend && pnpm test

frontend-lint:
	cd frontend && pnpm lint

frontend-typecheck:
	cd frontend && pnpm typecheck

frontend-build:
	cd frontend && pnpm build

test: agent-test backend-test frontend-test

lint: agent-lint backend-lint frontend-lint frontend-typecheck
