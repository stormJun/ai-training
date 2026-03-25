#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="$ROOT_DIR/.venv/bin/python"

if [[ ! -x "$VENV_PY" ]]; then
  echo "Missing shared venv interpreter: $VENV_PY" >&2
  exit 1
fi

"$VENV_PY" - <<'PY'
import importlib.util
import importlib.metadata as md
import sys

import langchain
import langgraph
print("Python:", sys.executable)
print("langchain:", langchain.__version__)
print("langchain-core:", md.version("langchain-core"))
print("langchain-community:", md.version("langchain-community"))
print("langchain-openai:", md.version("langchain-openai"))
print("langgraph:", md.version("langgraph"))
print("has langchain.memory:", importlib.util.find_spec("langchain.memory") is not None)
PY

echo
"$ROOT_DIR/.venv/bin/pip" check
