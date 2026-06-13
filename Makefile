.PHONY: adk-run env-check lint smoke-test test

adk-run:
	.venv/bin/adk run src/analyze_agent

env-check:
	.venv/bin/python -m analyze_agent

lint:
	.venv/bin/ruff check .

smoke-test:
	.venv/bin/python -m analyze_agent

test:
	.venv/bin/pytest
