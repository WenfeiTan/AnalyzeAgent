.PHONY: env-check lint smoke-test test

env-check:
	.venv/bin/python -m analyze_agent

lint:
	.venv/bin/ruff check .

smoke-test:
	.venv/bin/python -m analyze_agent

test:
	.venv/bin/pytest
