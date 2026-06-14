# Analyze Agent

Requirement analysis agent for the Asset Discovery workflow.

## Local Setup

Requirements:

- Python 3.11 through 3.14
- [uv](https://docs.astral.sh/uv/)
- A Gemini API key for runtime smoke checks

The repository contains three independent workspaces:

- `agent/`: reusable Python Analyze Agent package.
- `backend/`: FastAPI transport and demo runtime.
- `frontend/`: React, Vite and TypeScript interface.

```bash
cd agent && uv sync
cd ../backend && uv sync
cd ../frontend && pnpm install
cd ..

export GOOGLE_API_KEY="your-key"
make agent-env-check
make test
make lint
```

`.env.example` documents the supported settings. Export secrets through the
runtime environment; do not commit a populated `.env` file.

The dependency direction is `frontend -> backend -> agent`. The Agent remains an
in-process package and is not a third HTTP service.

The ADK root agent exposes:

- `analyze_initial`
- `analyze_update`
- `search_knowledge_base`

Until the real vector-mcp contract is available, the runtime binds
`search_knowledge_base` to `FakeKnowledgeBaseRetriever`.

Operational configuration and failure behavior are documented in
[`docs/runbook.md`](docs/runbook.md). The interactive demo is developed according
to [`docs/development-plan-2.0.md`](docs/development-plan-2.0.md).
