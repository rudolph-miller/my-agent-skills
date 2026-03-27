#!/usr/bin/env bash
set -euo pipefail

AUTH_FILE="${1:-./.agent-browser/auth.json}"
SESSION="${2:-restore}"
BASE_URL="${3:-http://localhost:3000}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ ! -f "$AUTH_FILE" ]]; then
  echo "AUTH_FILE_MISSING: $AUTH_FILE" >&2
  exit 2
fi

agent-browser --session "$SESSION" open "$BASE_URL"
agent-browser --session "$SESSION" wait --load networkidle
agent-browser --session "$SESSION" cookies clear || true
agent-browser --session "$SESSION" storage local clear || true
agent-browser --session "$SESSION" state load "$AUTH_FILE" || true

JS="$(python3 "$SCRIPT_DIR/build_restore_js.py" "$AUTH_FILE" "$BASE_URL")"

if [[ -z "$JS" ]]; then
  echo "AUTH_STATE_EMPTY: no localhost cookie/localStorage found in $AUTH_FILE" >&2
  exit 3
fi

agent-browser --session "$SESSION" eval "$JS"
agent-browser --session "$SESSION" open "${BASE_URL%/}/"
agent-browser --session "$SESSION" wait --load networkidle

echo "AUTH_RESTORED: session=$SESSION url=${BASE_URL%/}/"
