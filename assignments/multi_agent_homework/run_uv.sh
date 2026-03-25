#!/usr/bin/env bash
set -euo pipefail

# Helper to run MCP server or client with uv using the local .venv under assignments/multi_agent_homework.
# Usage: ./run_uv.sh server | client

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

VENV_PATH="$ROOT/.venv"
export UV_PROJECT_ENV="$VENV_PATH"

# Bootstrap env only inside assignments/multi_agent_homework/.venv
if [ ! -d "$VENV_PATH" ]; then
  uv sync
fi

case "${1:-}" in
  server)
    uv run python -m multi-agent.mcp_server.main
    ;;
  client)
    uv run python -m multi-agent.main
    ;;
  *)
    echo "Usage: $0 {server|client}"
    exit 1
    ;;
esac
