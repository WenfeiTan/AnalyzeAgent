.PHONY: agent-env-check agent-lint agent-run agent-test backend-lint backend-run \
	backend-test clean-data dev frontend-build frontend-dev frontend-lint \
	frontend-e2e frontend-test frontend-typecheck generate-api-types lint \
	smoke-test test

agent-env-check:
	cd agent && .venv/bin/python -m analyze_agent

agent-run:
	cd agent && ANALYZE_AGENT_DATABASE_PATH="$(CURDIR)/data/analyze-agent.sqlite3" \
		.venv/bin/adk run src/analyze_agent

agent-test:
	cd agent && .venv/bin/pytest

agent-lint:
	cd agent && .venv/bin/ruff check .

backend-run:
	cd backend && ANALYZE_AGENT_DATABASE_PATH="$(CURDIR)/data/analyze-agent.sqlite3" \
		.venv/bin/uvicorn analyze_api.app:app --reload

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

frontend-e2e:
	cd frontend && pnpm e2e

generate-api-types:
	backend/.venv/bin/python -m analyze_api.export_openapi frontend/openapi.json
	cd frontend && pnpm exec openapi-typescript openapi.json \
		-o src/api/generated/schema.ts

dev:
	./scripts/dev.sh

smoke-test:
	backend/.venv/bin/python scripts/smoke_test.py

clean-data:
	rm -f data/analyze-agent.sqlite3 data/analyze-agent.sqlite3-shm \
		data/analyze-agent.sqlite3-wal

test: agent-test backend-test frontend-test

lint: agent-lint backend-lint frontend-lint frontend-typecheck
