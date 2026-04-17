#!/usr/bin/env bash
set -euo pipefail

if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI is not installed or not in PATH" >&2
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "This script must be run inside a git repository." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"

MODE="${1:-}"
FEATURE="${2:-}"
DATE_ARG="${3:-}"
MODEL="${CODEX_MODEL:-gpt-5.4}"

if [[ "$MODE" != "inspect" || -z "$FEATURE" ]]; then
  echo "Usage: $0 inspect <feature-name> [YYYY-MM-DD]" >&2
  exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
ORIGINAL_REPO_NAME="$(basename "$(git rev-parse --path-format=absolute --git-common-dir | sed 's|/\\.git.*||')")"

if [[ -d "${REPO_ROOT}/docs/inspect-request" || -d "${REPO_ROOT}/docs/inspect" ]]; then
  REQUEST_DIR="docs/inspect-request"
  REPORT_DIR="docs/inspect"
else
  FALLBACK_BASE="/tmp/claude-dev/${ORIGINAL_REPO_NAME}"
  REQUEST_DIR="${FALLBACK_BASE}/inspect-request"
  REPORT_DIR="${FALLBACK_BASE}/inspect"
fi

mkdir -p "$REQUEST_DIR" "$REPORT_DIR"

resolve_file() {
  local dir="$1" feature="$2" date_arg="$3"
  if [[ -n "$date_arg" ]]; then
    echo "${dir}/${date_arg}-${feature}.md"
    return
  fi
  local found
  found="$(ls -1 "${dir}/"*"-${feature}.md" 2>/dev/null | sort | tail -1)"
  if [[ -n "$found" ]]; then
    echo "$found"
    return
  fi
  echo "${dir}/$(date '+%Y-%m-%d')-${feature}.md"
}

REQUEST_FILE="$(resolve_file "$REQUEST_DIR" "$FEATURE" "$DATE_ARG")"
REPORT_FILE="$(resolve_file "$REPORT_DIR" "$FEATURE" "$DATE_ARG")"

if [[ ! -f "$REQUEST_FILE" ]]; then
  echo "Missing inspect request file: $REQUEST_FILE" >&2
  exit 1
fi

PROMPT="$(cat "$REQUEST_FILE")

$(printf '\n')

$(cat "${SKILL_ROOT}/references/inspect-prompt-template.md")

$(printf '\n')

$(cat "${SKILL_ROOT}/references/inspect-template.md")"

codex exec --full-auto --model "$MODEL" --output-last-message "$REPORT_FILE" "$PROMPT"
echo "Inspect report written to $REPORT_FILE"
