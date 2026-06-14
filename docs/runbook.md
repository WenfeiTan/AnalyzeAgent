# Analyze Agent Runbook

## Local Setup

```bash
cd agent && uv sync
cd ../backend && uv sync
cd ../frontend && pnpm install
cd ..
export GOOGLE_API_KEY="..."
make agent-env-check
make test
make lint
```

Run the ADK CLI:

```bash
make agent-run
```

Run the Backend shell:

```bash
make backend-run
```

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

Never commit a populated `.env` file or print `GOOGLE_API_KEY`.

## Current Knowledge Base Mode

The runtime currently binds `FakeKnowledgeBaseRetriever`.

- Unknown queries return empty chunks.
- Unit fixtures cover complete, partial, irrelevant, timeout, and invalid results.
- No MCP server, embeddings, cosine similarity, or real vector-mcp transport is
  implemented in this repository.
- `codex/vector-mcp-adapter` remains deferred until the external request and
  response contract is available.

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

Use `analyze_agent.observability.METRICS.snapshot()` for local inspection. A
production telemetry exporter is intentionally deferred until deployment
infrastructure is selected.

## Expected Failure Behavior

### Missing API key

`make env-check` fails with a clear `GOOGLE_API_KEY` configuration error.

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
make agent-lint
make backend-lint
make frontend-lint
make frontend-typecheck
make frontend-build
GOOGLE_API_KEY=test-placeholder make agent-env-check
git diff --check
```

The placeholder key checks configuration and imports only; it does not send a
Gemini request.
