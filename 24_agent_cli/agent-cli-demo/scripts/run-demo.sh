#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVER_URL="${SERVER_URL:-http://127.0.0.1:8787}"
export AGENT_CLI_DEMO_HOME="${AGENT_CLI_DEMO_HOME:-$ROOT_DIR/.demo-data}"

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "$SERVER_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

rm -rf "$AGENT_CLI_DEMO_HOME"
mkdir -p "$AGENT_CLI_DEMO_HOME"

printf '\n[1/6] Starting mock server at %s\n' "$SERVER_URL"
pnpm --dir "$ROOT_DIR/server" start >/tmp/agent-cli-demo-server.log 2>&1 &
SERVER_PID=$!
sleep 1

printf '\n[2/6] Expect AUTH_REQUIRED before login\n'
set +e
UNAUTH_OUT="$("$ROOT_DIR/bin/mp-admin-cli" dashboard summary --server "$SERVER_URL" 2>/dev/null)"
UNAUTH_CODE=$?
set -e
printf 'exit=%s\n%s\n' "$UNAUTH_CODE" "$UNAUTH_OUT"
if [[ "$UNAUTH_CODE" -ne 10 ]]; then
  echo "expected exit code 10 before login" >&2
  exit 1
fi

printf '\n[3/6] Running login and waiting for approval\n'
LOGIN_STDOUT="$(mktemp)"
LOGIN_STDERR="$(mktemp)"
"$ROOT_DIR/bin/mp-sso-cli" login --server "$SERVER_URL" >"$LOGIN_STDOUT" 2>"$LOGIN_STDERR" &
LOGIN_PID=$!

APPROVAL_URL=""
for _ in 1 2 3 4 5; do
  APPROVAL_URL="$(grep -Eo "${SERVER_URL//\//\\/}/mock/approve\\?user_code=[A-Z0-9_]+" "$LOGIN_STDERR" | head -n1 || true)"
  if [[ -n "$APPROVAL_URL" ]]; then
    break
  fi
  sleep 1
done

if [[ -z "$APPROVAL_URL" ]]; then
  echo "approval url not found in login output" >&2
  cat "$LOGIN_STDERR" >&2
  exit 1
fi

curl -s "$APPROVAL_URL" >/dev/null
wait "$LOGIN_PID"
printf '%s\n' "$(cat "$LOGIN_STDOUT")"

printf '\n[4/6] Fetching dashboard summary after login\n'
SUMMARY_OUT="$("$ROOT_DIR/bin/mp-admin-cli" dashboard summary)"
printf '%s\n' "$SUMMARY_OUT"

printf '\n[5/6] Reading cached login status\n'
STATUS_OUT="$("$ROOT_DIR/bin/mp-sso-cli" status)"
printf '%s\n' "$STATUS_OUT"

printf '\n[6/6] Logging out\n'
LOGOUT_OUT="$("$ROOT_DIR/bin/mp-sso-cli" logout)"
printf '%s\n' "$LOGOUT_OUT"

rm -f "$LOGIN_STDOUT" "$LOGIN_STDERR"
