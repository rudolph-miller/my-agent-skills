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

# Resolve the directory where this script lives, then derive the skill root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"

AUTH_ERROR_PATTERNS='Refresh token is invalid|TokenRefreshFailed|invalid_grant'

MODE="${1:-}"
FEATURE="${2:-}"
DATE_ARG="${3:-}"
MODEL="${CODEX_MODEL:-gpt-5.4}"

if [[ "$MODE" != "review" || -z "$FEATURE" ]]; then
  echo "Usage: $0 review <feature-name> [YYYY-MM-DD]" >&2
  exit 1
fi

# Resolve directories: use docs/ if it exists, otherwise /tmp/claude-dev/<repo>/
# Review output always goes to tmp/ to avoid bloating git history
REPO_ROOT="$(git rev-parse --show-toplevel)"
ORIGINAL_REPO_NAME="$(basename "$(git rev-parse --path-format=absolute --git-common-dir | sed 's|/\.git.*||')")"
TMP_DIR="${REPO_ROOT}/tmp"
if [[ -d "${REPO_ROOT}/docs/prd" || -d "${REPO_ROOT}/docs/todo" ]]; then
  PRD_DIR="docs/prd"
  TODO_DIR="docs/todo"
  PROPOSAL_DIR="docs/proposal"
else
  FALLBACK_BASE="/tmp/claude-dev/${ORIGINAL_REPO_NAME}"
  PRD_DIR="${FALLBACK_BASE}/prd"
  TODO_DIR="${FALLBACK_BASE}/todo"
  PROPOSAL_DIR="${FALLBACK_BASE}/proposal"
fi
REVIEW_DIR="${TMP_DIR}/review"

mkdir -p "$PRD_DIR" "$TODO_DIR" "$PROPOSAL_DIR" "$REVIEW_DIR"

# Resolve file paths: explicit date > glob search > today's date
resolve_file() {
  local dir="$1" feature="$2" date_arg="$3" prefix="${4:-}"
  if [[ -n "$date_arg" ]]; then
    echo "${dir}/${prefix}${date_arg}-${feature}.md"
    return
  fi
  # Search for *-<feature>.md (with optional prefix), pick the latest (sorted last)
  local found
  found="$(ls -1 "${dir}/${prefix}"*"-${feature}.md" 2>/dev/null | sort | tail -1)"
  if [[ -n "$found" ]]; then
    echo "$found"
    return
  fi
  # Fallback to today's date
  echo "${dir}/${prefix}$(date '+%Y-%m-%d')-${feature}.md"
}

PROPOSAL_FILE="$(resolve_file "$PROPOSAL_DIR" "$FEATURE" "$DATE_ARG")"
REVIEW_FILE="$(resolve_file "$REVIEW_DIR" "$FEATURE" "$DATE_ARG" "next-action-")"

if [[ ! -f "$PROPOSAL_FILE" ]]; then
  echo "Missing proposal file: $PROPOSAL_FILE" >&2
  echo "Searched in: ${PROPOSAL_DIR}/*-${FEATURE}.md" >&2
  exit 1
fi

# Collect existing PRD/Todo files for context (optional, may not exist)
CONTEXT=""
for prd in "${PRD_DIR}/"*"-${FEATURE}.md" "${PRD_DIR}/"*.md; do
  if [[ -f "$prd" ]]; then
    CONTEXT="${CONTEXT}

--- PRD: $(basename "$prd") ---
$(cat "$prd")"
  fi
done 2>/dev/null || true

for todo in "${TODO_DIR}/"*"-${FEATURE}.md" "${TODO_DIR}/"*.md; do
  if [[ -f "$todo" ]]; then
    CONTEXT="${CONTEXT}

--- Todo: $(basename "$todo") ---
$(cat "$todo")"
  fi
done 2>/dev/null || true

# Build prompt: context + proposal + review template
PROMPT="${CONTEXT}

--- Proposal ---
$(cat "$PROPOSAL_FILE")

$(cat "${SKILL_ROOT}/references/review-prompt-template.md")"

run_codex_exec() {
  local log_file pid status=0 auth_failed=0
  log_file="$(mktemp)"

  codex exec --full-auto --model "$MODEL" "$PROMPT" \
    > >(tee -a "$log_file") \
    2> >(tee -a "$log_file" >&2) &
  pid=$!

  while kill -0 "$pid" >/dev/null 2>&1; do
    if grep -Eiq "$AUTH_ERROR_PATTERNS" "$log_file"; then
      auth_failed=1
      echo "Codex authentication failed. Re-run after refreshing Codex login." >&2
      kill "$pid" >/dev/null 2>&1 || true
      break
    fi
    sleep 1
  done

  set +e
  wait "$pid"
  status=$?
  set -e

  if (( auth_failed )) || grep -Eiq "$AUTH_ERROR_PATTERNS" "$log_file"; then
    rm -f "$log_file"
    return 86
  fi

  rm -f "$log_file"
  return "$status"
}

run_codex_exec | tee "$REVIEW_FILE"
echo "Review written to $REVIEW_FILE"
