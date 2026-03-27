#!/usr/bin/env bash
set -euo pipefail

AUTH_FILE="${1:-./.agent-browser/auth.json}"
SESSION="${2:-restore}"
BASE_URL="${3:-http://localhost:3000}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ -f "$AUTH_FILE" ]]; then
  "$SCRIPT_DIR/restore_localhost_auth.sh" "$AUTH_FILE" "$SESSION" "$BASE_URL"
  exit 0
fi

mkdir -p "$(dirname "$AUTH_FILE")"
agent-browser --session "$SESSION" open "$BASE_URL" --headed

echo "LOGIN_REQUIRED: Googleログインを完了してください。"
echo "完了後に以下を実行:"
echo "  $SCRIPT_DIR/save_auth_state.sh $AUTH_FILE $SESSION"

exit 10
