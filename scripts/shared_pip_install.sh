#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIP="$ROOT_DIR/.venv/bin/pip"
CONSTRAINTS="$ROOT_DIR/constraints.shared.txt"

if [[ ! -x "$PIP" ]]; then
  echo "Missing pip in shared venv: $PIP" >&2
  exit 1
fi

if [[ ! -f "$CONSTRAINTS" ]]; then
  echo "Missing constraints file: $CONSTRAINTS" >&2
  exit 1
fi

if [[ $# -lt 1 ]]; then
  echo "Usage: scripts/shared_pip_install.sh <package...>" >&2
  echo "Example: scripts/shared_pip_install.sh langchain-community==0.3.29" >&2
  exit 2
fi

exec "$PIP" install -c "$CONSTRAINTS" "$@"

