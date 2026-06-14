# Analyze Agent Runbook

## Local Setup

```bash
cd agent && uv sync
cd ../backend && uv sync
cd ../frontend && pnpm install
pnpm exec playwright install chromium
cd ..
export GOOGLE_API_KEY="..."
make agent-env-check
make test
make lint
```

Run the complete interactive demo:

```bash
make dev
```

This starts:

- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8000`
- OpenAPI: `http://127.0.0.1:8000/api/v1/openapi.json`
- Metrics: `http://127.0.0.1:8000/api/v1/metrics`
- SQLite: `<repository>/data/analyze-agent.sqlite3`

Use `make agent-run`, `make backend-run`, or `make frontend-dev` to start one
workspace independently.

## Runtime Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `GOOGLE_API_KEY` | required | Gemini API authentication |
| `ANALYZE_AGENT_MODEL` | `gemini-2.5-flash` | Gemini model ID |
| `ANALYZE_AGENT_LOG_LEVEL` | `INFO` | Python log level |
| `ANALYZE_AGENT_DATABASE_PATH` | `data/analyze-agent.sqlite3` | SQLite database, relative to the running process |
| `ANALYZE_AGENT_MODEL_TIMEOUT_SECONDS` | `30` | Per model attempt timeout |
| `ANALYZE_AGENT_RETRIEVER_TIMEOUT_SECONDS` | `10` | Per retrieval attempt timeout |
| `ANALYZE_AGENT_MAX_ATTEMPTS` | `2` | Bounded external-call attempts |
| `ANALYZE_AGENT_SCHEMA_REPAIR_ATTEMPTS` | `1` | Bounded structured-output repair |
| `ANALYZE_API_ALLOWED_ORIGINS` | local ports | Backend CORS allowlist |
| `ANALYZE_API_MAX_JOBS` | `100` | Bounded process-local Web job retention |
| `ANALYZE_API_MAX_EVENTS_PER_JOB` | `200` | Bounded events retained per job |
| `ANALYZE_API_EVENT_POLL_SECONDS` | `0.05` | SSE polling interval |
| `VITE_ANALYZE_API_BASE_URL` | `http://localhost:8000` | Frontend Backend URL |

Never commit a populated `.env` file or print `GOOGLE_API_KEY`.

`make dev` sets an absolute repository-local database path unless
`ANALYZE_AGENT_DATABASE_PATH` is already set. Direct commands should also use
an absolute path to avoid creating separate databases under `agent/` and
`backend/`.

## Current Knowledge Base Mode

The demo runtime currently binds `FakeKnowledgeBaseRetriever`.

- Packaged resources cover empty, complete mapping, partial mapping, no valid
  evidence, timeout, and invalid response scenarios.
- Each Web job selects one isolated scenario.
- No MCP server, embeddings, cosine similarity, or real vector-mcp transport is
  implemented in this repository.
- `codex/vector-mcp-adapter` remains deferred until the external request and
  response contract is available.

To replace the fake service later:

1. Implement `KnowledgeBaseRetriever.search(text) -> list[KnowledgeChunk]`.
2. Translate the external chunk payload into the existing typed `KnowledgeChunk`.
3. Bind the adapter in runtime composition without changing workflows or UI.
4. Add adapter contract tests for timeout, invalid response and chunk metadata.
5. Change the configuration provider label only after real transport is active.

## Logs

Logs are JSON and contain operational metadata only:

- timestamp
- level
- event
- request ID
- requirement ID
- revision ID
- duration
- chunk count
- exception type

Raw requirements, supplemental information, chunk text, feedback reasons, and
API keys must not be logged. Sensitive field names such as `api_key`,
`authorization`, `password`, `secret`, and `token` are redacted.

## Metrics

The first version keeps process-local counters and observations:

- `tool_calls.<tool>`
- `tool_failures.<tool>`
- `tool_duration_ms.<tool>`
- `web_jobs.submitted`
- `web_jobs.completed`
- `web_jobs.failed`
- `web_stage_events.<stage>.<status>`
- `web_stage_duration_ms.<stage>`

Use `analyze_agent.observability.METRICS.snapshot()` for local inspection. A
Web snapshot is available from `GET /api/v1/metrics`. A production telemetry
exporter is intentionally deferred until deployment infrastructure is selected.

Web logs include job ID, request ID, stage, status, duration and safe error code.
They do not include requirement text, chunk text or feedback content.

## Expected Failure Behavior

### Missing API key

The Backend remains healthy and the page reports `Gemini API key missing`.
Submission buttons stay disabled. `make agent-env-check` fails with a clear
configuration error.

### Gemini timeout or retryable error

The runtime performs at most `ANALYZE_AGENT_MAX_ATTEMPTS`. Initial or Updated
analysis fails after the bounded attempts; it never fabricates a result.

### Retriever timeout

Retrieval performs bounded attempts, then Initial/Updated analysis continues
without Knowledge Base reuse and adds a warning.

### Invalid structured model output

Gemini receives at most `ANALYZE_AGENT_SCHEMA_REPAIR_ATTEMPTS` repair prompts.
The workflow fails if no valid typed response is produced.

### Prompt-injection-like text

Requirement and chunk text remain untrusted data. The workflow records a
generic warning and does not execute instructions found in that text.

### Concurrent requirement update

SQLite compares the code-read base revision number inside a write transaction.
A stale update raises `RevisionConflictError`; the caller must read the latest
revision and rerun analysis.

## Verification

```bash
make agent-test
make backend-test
make frontend-test
make frontend-e2e
make agent-lint
make backend-lint
make frontend-lint
make frontend-typecheck
make frontend-build
make generate-api-types
GOOGLE_API_KEY=test-placeholder make agent-env-check
git diff --check
```

The placeholder key checks configuration and imports only; it does not send a
Gemini request.

The Python API E2E suite uses injected deterministic model adapters and exercises:

- Initial empty Knowledge Base.
- Initial successful mapping reuse.
- Update with supplemental information.
- Update with accepted search feedback.
- Retriever timeout degradation.

Playwright validates Initial result/debug rendering and Update/History
interactions against the versioned HTTP/SSE contract.

## Health And Cleanup

With `make dev` running:

```bash
make smoke-test
```

This checks health, configuration, explicit Fake Knowledge Base mode and metrics.

Stop `make dev` with `Ctrl-C`. Remove local requirement history with:

```bash
make clean-data
```

The command removes only the known repository-local SQLite database and its WAL
files.
