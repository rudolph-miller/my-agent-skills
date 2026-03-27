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

MODE="${1:-}"
FEATURE="${2:-}"
MODEL="${CODEX_MODEL:-gpt-5.4}"

if [[ -z "$MODE" || -z "$FEATURE" ]]; then
  echo "Usage: $0 <review|implement|fix> <feature-name>" >&2
  exit 1
fi

DATE_PREFIX="$(date '+%Y-%m-%d')"

# Resolve directories: use docs/ if it exists, otherwise /tmp/claude-dev/<repo>/
REPO_ROOT="$(git rev-parse --show-toplevel)"
if [[ -d "${REPO_ROOT}/docs/prd" || -d "${REPO_ROOT}/docs/todo" ]]; then
  PRD_DIR="docs/prd"
  TODO_DIR="docs/todo"
  REVIEW_DIR="docs/review"
else
  FALLBACK_BASE="/tmp/claude-dev/$(basename "$REPO_ROOT")"
  PRD_DIR="${FALLBACK_BASE}/prd"
  TODO_DIR="${FALLBACK_BASE}/todo"
  REVIEW_DIR="${FALLBACK_BASE}/review"
fi

PRD_FILE="${PRD_DIR}/${DATE_PREFIX}-${FEATURE}.md"
TODO_FILE="${TODO_DIR}/${DATE_PREFIX}-${FEATURE}.md"
REVIEW_FILE="${REVIEW_DIR}/${DATE_PREFIX}-${FEATURE}.md"

mkdir -p "$PRD_DIR" "$TODO_DIR" "$REVIEW_DIR"

if [[ ! -f "$TODO_FILE" ]]; then
  echo "Missing TODO file: $TODO_FILE" >&2
  exit 1
fi

get_session_id() {
  python3 - "$TODO_FILE" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
m = re.search(r'^codex_session_id:\s*(.+?)\s*$', text, re.M)
print(m.group(1).strip() if m else "")
PY
}

save_session_id() {
  local session_id="$1"
  python3 - "$TODO_FILE" "$session_id" <<'PY'
import re, sys
path, sid = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()
if text.startswith('---\n'):
    end = text.find('\n---', 4)
    if end != -1:
        fm = text[4:end]
        body = text[end+4:]
        if re.search(r'(?m)^codex_session_id:', fm):
            fm = re.sub(r'(?m)^codex_session_id:.*$', f'codex_session_id: {sid}', fm)
        else:
            fm = fm.rstrip() + f'\ncodex_session_id: {sid}\n'
        out = f'---\n{fm}---{body}'
    else:
        out = f'---\ncodex_session_id: {sid}\n---\n\n' + text
else:
    out = f'---\ncodex_session_id: {sid}\n---\n\n' + text
with open(path, 'w', encoding='utf-8') as f:
    f.write(out)
PY
}

extract_session_id_from_jsonl() {
  local jsonl_file="$1"
  python3 - "$jsonl_file" <<'PY'
import json, re, sys
path = sys.argv[1]
sid = ""
with open(path, encoding="utf-8") as f:
    for line in f:
        line=line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        # Try known shapes first
        for key in ("session_id", "thread_id", "conversation_id"):
            if isinstance(obj, dict) and isinstance(obj.get(key), str):
                sid = obj[key]
                break
        if sid:
            break
        blob = json.dumps(obj, ensure_ascii=False)
        m = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', blob, re.I)
        if m:
            sid = m.group(1)
            break
print(sid)
PY
}

case "$MODE" in
  review)
    if [[ ! -f "$PRD_FILE" ]]; then
      echo "Missing PRD file: $PRD_FILE" >&2
      exit 1
    fi
    PROMPT="$(cat "$PRD_FILE")

$(printf '\n')

$(cat "$TODO_FILE")

$(printf '\n')

$(cat .claude/skills/dev-codex-review-prd-todo/references/review-prompt-template.md)"
    codex exec --model "$MODEL" "$PROMPT" | tee "$REVIEW_FILE"
    echo "Review written to $REVIEW_FILE"
    ;;

  implement)
    if [[ ! -f "$PRD_FILE" ]]; then
      echo "Missing PRD file: $PRD_FILE" >&2
      exit 1
    fi
    TMP_JSONL="$(mktemp)"
    PROMPT="$(cat "$PRD_FILE")

$(printf '\n')

$(cat "$TODO_FILE")

$(printf '\n')

$(cat .claude/skills/dev-codex-implement/references/implement-prompt-template.md)"
    codex exec --json --model "$MODEL" "$PROMPT" | tee "$TMP_JSONL"
    SID="$(extract_session_id_from_jsonl "$TMP_JSONL")"
    rm -f "$TMP_JSONL"
    if [[ -n "$SID" ]]; then
      save_session_id "$SID"
      echo "Saved codex_session_id=$SID to $TODO_FILE"
    else
      echo "Warning: could not extract session id from codex output." >&2
    fi
    ;;

  fix)
    SID="$(get_session_id)"
    if [[ -z "$SID" ]]; then
      echo "No codex_session_id found in $TODO_FILE" >&2
      exit 1
    fi
    PROMPT="$(cat "$TODO_FILE")

$(printf '\n')

$(cat .claude/skills/dev-codex-implement/references/fix-prompt-template.md)"
    codex exec resume "$SID" "$PROMPT"
    ;;

  *)
    echo "Unknown mode: $MODE" >&2
    echo "Usage: $0 <review|implement|fix> <feature-name>" >&2
    exit 1
    ;;
esac
