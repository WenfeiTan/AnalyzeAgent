#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "${ROOT_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.env"
  set +a
fi

export ANALYZE_AGENT_DATABASE_PATH="${ANALYZE_AGENT_DATABASE_PATH:-${ROOT_DIR}/data/analyze-agent.sqlite3}"
export VITE_ANALYZE_API_BASE_URL="${VITE_ANALYZE_API_BASE_URL:-http://localhost:8000}"

mkdir -p "${ROOT_DIR}/data"

cleanup() {
  trap - INT TERM EXIT
  kill "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
  wait "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

(
  cd "${ROOT_DIR}/backend"
  exec .venv/bin/uvicorn analyze_api.app:app --reload --host 127.0.0.1 --port 8000
) &
BACKEND_PID=$!

(
  cd "${ROOT_DIR}/frontend"
  exec pnpm dev --host 127.0.0.1 --port 5173
) &
FRONTEND_PID=$!

echo "Analyze Agent Backend:  http://127.0.0.1:8000"
echo "Analyze Agent Frontend: http://127.0.0.1:5173"
echo "SQLite: ${ANALYZE_AGENT_DATABASE_PATH}"

wait "${BACKEND_PID}" "${FRONTEND_PID}"
