# Analyze Agent

Requirement analysis agent for the Asset Discovery workflow.

## Local Setup

Requirements:

- Python 3.11 through 3.14
- [uv](https://docs.astral.sh/uv/)
- A Gemini API key for runtime smoke checks

```bash
uv sync
export GOOGLE_API_KEY="your-key"
make env-check
make test
```

`.env.example` documents the supported settings. Export secrets through the
runtime environment; do not commit a populated `.env` file.

The repository currently contains the Google ADK bootstrap. Domain workflows are
implemented incrementally according to
[`docs/development-branch-plan.md`](docs/development-branch-plan.md).
