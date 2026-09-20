#!/usr/bin/env bash
# Boot the Pacioli development environment: FastAPI backend + Vite dev server.
# Both processes are stopped when the script exits (Ctrl+C).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_PORT="${PACIOLI_API_PORT:-8000}"
FRONTEND_PORT="${PACIOLI_FRONTEND_PORT:-5173}"

cleanup() {
  if [[ -n "${API_PID:-}" ]]; then kill "$API_PID" 2>/dev/null || true; fi
  if [[ -n "${FRONT_PID:-}" ]]; then kill "$FRONT_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM

echo "Pacioli dev environment"
echo "  API:      http://localhost:${API_PORT}  (docs: /docs)"
echo "  Frontend: http://localhost:${FRONTEND_PORT}"
echo

"$ROOT/backend/.venv/bin/uvicorn" app.main:app \
  --app-dir "$ROOT/backend" \
  --port "$API_PORT" &
API_PID=$!

npm --prefix "$ROOT/frontend" run dev -- --port "$FRONTEND_PORT" --strictPort &
FRONT_PID=$!

wait
