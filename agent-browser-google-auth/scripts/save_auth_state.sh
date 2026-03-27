#!/usr/bin/env bash
set -euo pipefail

AUTH_FILE="${1:-./.agent-browser/auth.json}"
SESSION="${2:-restore}"

mkdir -p "$(dirname "$AUTH_FILE")"

if agent-browser --session "$SESSION" state save "$AUTH_FILE" >/dev/null 2>&1; then
  :
else
  agent-browser state save "$AUTH_FILE"
fi

echo "AUTH_SAVED: $AUTH_FILE"
