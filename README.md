# Analyze Agent

Requirement analysis agent for the Asset Discovery workflow.

## Local Setup

Requirements:

- Python 3.11 through 3.14
- [uv](https://docs.astral.sh/uv/)
- Node.js and pnpm 10
- A Gemini API key for runtime smoke checks

The repository contains three independent workspaces:

- `agent/`: reusable Python Analyze Agent package.
- `backend/`: FastAPI transport and demo runtime.
- `frontend/`: React, Vite and TypeScript interface.

```bash
cd agent && uv sync
cd ../backend && uv sync
cd ../frontend && pnpm install
pnpm exec playwright install chromium
cd ..

export GOOGLE_API_KEY="your-key"
make agent-env-check
make test
make lint
make frontend-e2e
```

`.env.example` documents the supported settings. Export secrets through the
runtime environment; do not commit a populated `.env` file.

The dependency direction is `frontend -> backend -> agent`. The Agent remains an
in-process package and is not a third HTTP service.

## Interactive Demo

Start both applications from the repository root:

```bash
export GOOGLE_API_KEY="your-key"
make dev
```

Open `http://127.0.0.1:5173`. The Backend runs at
`http://127.0.0.1:8000`, and the shared SQLite file is
`data/analyze-agent.sqlite3`.

The page supports:

- Initial requirement analysis.
- Update from supplemental information or structured search feedback.
- Real SSE workflow stages.
- Clear fields, keywords, reused source mappings and warnings.
- SQLite requirement/revision history.
- Folded request, response and trace payloads.

Fake Knowledge Base scenarios are explicitly labelled and loaded from
`agent/src/analyze_agent/demo_resources/`. They do not call vector-mcp.

Useful local commands:

```bash
make smoke-test
make clean-data
```

The ADK root agent exposes:

- `analyze_initial`
- `analyze_update`
- `search_knowledge_base`

Until the real vector-mcp contract is available, the runtime binds
`search_knowledge_base` to `FakeKnowledgeBaseRetriever`.

Operational configuration and failure behavior are documented in
[`docs/runbook.md`](docs/runbook.md). The interactive demo is developed according
to [`docs/development-plan-2.0.md`](docs/development-plan-2.0.md).
