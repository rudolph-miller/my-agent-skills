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
shift 2 2>/dev/null || true

DATE_ARG=""
GROUP=""
MODEL="${CODEX_MODEL:-gpt-5.4}"

# Parse remaining args: [YYYY-MM-DD] [--group <name>]
while [[ $# -gt 0 ]]; do
  case "$1" in
    --group)
      GROUP="${2:-}"
      shift 2
      ;;
    *)
      DATE_ARG="$1"
      shift
      ;;
  esac
done

if [[ -z "$MODE" || -z "$FEATURE" ]]; then
  echo "Usage: $0 <review|implement|fix> <feature-name> [YYYY-MM-DD] [--group <group>]" >&2
  exit 1
fi

# Resolve directories: use docs/ if it exists, otherwise /tmp/claude-dev/<repo>/
# Review output always goes to tmp/ to avoid bloating git history
REPO_ROOT="$(git rev-parse --show-toplevel)"
# In a worktree, --git-common-dir points to the original repo's .git,
# so we derive the stable repo name from it (avoids worktree dir name mismatch).
ORIGINAL_REPO_NAME="$(basename "$(git rev-parse --path-format=absolute --git-common-dir | sed 's|/\.git.*||')")"
TMP_DIR="${REPO_ROOT}/tmp"
if [[ -d "${REPO_ROOT}/docs/prd" || -d "${REPO_ROOT}/docs/todo" ]]; then
  PRD_DIR="docs/prd"
  TODO_DIR="docs/todo"
else
  FALLBACK_BASE="/tmp/claude-dev/${ORIGINAL_REPO_NAME}"
  PRD_DIR="${FALLBACK_BASE}/prd"
  TODO_DIR="${FALLBACK_BASE}/todo"
fi
REVIEW_DIR="${TMP_DIR}/review"

mkdir -p "$PRD_DIR" "$TODO_DIR" "$REVIEW_DIR"

# Resolve file paths: explicit date > glob search > today's date
resolve_file() {
  local dir="$1" feature="$2" date_arg="$3"
  if [[ -n "$date_arg" ]]; then
    echo "${dir}/${date_arg}-${feature}.md"
    return
  fi
  # Search for *-<feature>.md, pick the latest (sorted last)
  local found
  found="$(ls -1 "${dir}/"*"-${feature}.md" 2>/dev/null | sort | tail -1)"
  if [[ -n "$found" ]]; then
    echo "$found"
    return
  fi
  # Fallback to today's date
  echo "${dir}/$(date '+%Y-%m-%d')-${feature}.md"
}

PRD_FILE="$(resolve_file "$PRD_DIR" "$FEATURE" "$DATE_ARG")"
TODO_FILE="$(resolve_file "$TODO_DIR" "$FEATURE" "$DATE_ARG")"
REVIEW_FILE="$(resolve_file "$REVIEW_DIR" "$FEATURE" "$DATE_ARG")"

if [[ ! -f "$TODO_FILE" ]]; then
  echo "Missing TODO file: $TODO_FILE" >&2
  echo "Searched in: ${TODO_DIR}/*-${FEATURE}.md" >&2
  exit 1
fi

# Extract the content for a specific group from the Todo file.
# If no group is specified, return the full content (minus frontmatter).
extract_group_content() {
  local todo_file="$1" group="$2"
  python3 - "$todo_file" "$group" <<'PY'
import re, sys

path, group = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()

# Strip frontmatter
body = text
if body.startswith('---\n'):
    end = body.find('\n---', 4)
    if end != -1:
        body = body[end+4:].lstrip('\n')

if not group:
    print(body)
    sys.exit(0)

# Extract the section for the given group
pattern = rf'^## Group:\s*{re.escape(group)}\s*$'
lines = body.split('\n')
collecting = False
result = []
for line in lines:
    if re.match(r'^## Group:\s*', line):
        if re.match(pattern, line):
            collecting = True
            result.append(line)
        else:
            collecting = False
    elif re.match(r'^## ', line) and not re.match(r'^## Group:', line):
        # Non-group H2 (e.g. ## Notes) — stop collecting
        collecting = False
    elif collecting:
        result.append(line)

if not result:
    print(f"Error: Group '{group}' not found in {path}", file=sys.stderr)
    sys.exit(1)

print('\n'.join(result))
PY
}

# List all group names from the Todo file
list_groups() {
  local todo_file="$1"
  python3 - "$todo_file" <<'PY'
import re, sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
groups = re.findall(r'^## Group:\s*(.+?)\s*$', text, re.M)
for g in groups:
    print(g)
PY
}

# Get session id for a specific group (or the single session id for backward compat)
get_session_id() {
  local group="${1:-}"
  python3 - "$TODO_FILE" "$group" <<'PY'
import re, sys, json

path, group = sys.argv[1], sys.argv[2]
text = open(path, encoding="utf-8").read()

# Try codex_session_ids (new format: YAML-ish JSON map)
m = re.search(r'^codex_session_ids:\s*(.+?)$', text, re.M)
if m:
    raw = m.group(1).strip()
    if raw and raw != '{}':
        try:
            ids = json.loads(raw.replace("'", '"'))
            if group and group in ids:
                print(ids[group])
                sys.exit(0)
            elif not group and len(ids) == 1:
                print(list(ids.values())[0])
                sys.exit(0)
        except Exception:
            pass

# Fallback: try old codex_session_id (single value)
m = re.search(r'^codex_session_id:\s*(.+?)\s*$', text, re.M)
if m and m.group(1).strip():
    print(m.group(1).strip())
else:
    print("")
PY
}

# Save session id for a specific group
save_session_id() {
  local session_id="$1" group="${2:-}"
  python3 - "$TODO_FILE" "$session_id" "$group" <<'PY'
import re, sys, json

path, sid, group = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(path, encoding="utf-8").read()

if not text.startswith('---\n'):
    text = '---\ncodex_session_ids: {}\n---\n\n' + text

end = text.find('\n---', 4)
if end == -1:
    text = '---\ncodex_session_ids: {}\n---\n\n' + text
    end = text.find('\n---', 4)

fm = text[4:end]
body = text[end+4:]

# Parse existing codex_session_ids
m = re.search(r'^codex_session_ids:\s*(.+?)$', fm, re.M)
ids = {}
if m:
    raw = m.group(1).strip()
    if raw and raw != '{}':
        try:
            ids = json.loads(raw.replace("'", '"'))
        except Exception:
            ids = {}

# Update the map
key = group if group else "default"
ids[key] = sid

ids_json = json.dumps(ids, ensure_ascii=False)

if m:
    fm = re.sub(r'^codex_session_ids:\s*.+?$', f'codex_session_ids: {ids_json}', fm, flags=re.M)
else:
    fm = fm.rstrip() + f'\ncodex_session_ids: {ids_json}\n'

# Remove old codex_session_id if present
fm = re.sub(r'\n?codex_session_id:.*\n?', '\n', fm)

out = f'---\n{fm.strip()}\n---{body}'
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

run_codex_exec() {
  local prompt="$1"
  shift || true
  local log_file pid status=0 auth_failed=0
  log_file="$(mktemp)"

  codex exec --full-auto --model "$MODEL" "$@" "$prompt" \
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

$(cat "$(dirname "$SKILL_ROOT")/dev-codex-plan/references/review-prompt-template.md")"
    run_codex_exec "$PROMPT" | tee "$REVIEW_FILE"
    echo "Review written to $REVIEW_FILE"
    ;;

  implement)
    if [[ ! -f "$PRD_FILE" ]]; then
      echo "Missing PRD file: $PRD_FILE" >&2
      exit 1
    fi
    TMP_JSONL="$(mktemp)"
    TODO_CONTENT="$(extract_group_content "$TODO_FILE" "$GROUP")"
    PROMPT="$(cat "$PRD_FILE")

$(printf '\n')

${TODO_CONTENT}

$(printf '\n')

$(cat "${SKILL_ROOT}/references/implement-prompt-template.md")"
    run_codex_exec "$PROMPT" --json | tee "$TMP_JSONL"
    SID="$(extract_session_id_from_jsonl "$TMP_JSONL")"
    rm -f "$TMP_JSONL"
    if [[ -n "$SID" ]]; then
      save_session_id "$SID" "$GROUP"
      echo "Saved codex_session_id=$SID (group=${GROUP:-default}) to $TODO_FILE"
    else
      echo "Warning: could not extract session id from codex output." >&2
    fi
    ;;

  fix)
    SID="$(get_session_id "$GROUP")"
    if [[ -z "$SID" ]]; then
      echo "No codex_session_id found in $TODO_FILE (group=${GROUP:-default})" >&2
      exit 1
    fi
    TODO_CONTENT="$(extract_group_content "$TODO_FILE" "$GROUP")"
    PROMPT="${TODO_CONTENT}

$(printf '\n')

$(cat "${SKILL_ROOT}/references/fix-prompt-template.md")"
    codex exec resume "$SID" "$PROMPT"
    ;;

  list-groups)
    list_groups "$TODO_FILE"
    ;;

  *)
    echo "Unknown mode: $MODE" >&2
    echo "Usage: $0 <review|implement|fix|list-groups> <feature-name> [YYYY-MM-DD] [--group <group>]" >&2
    exit 1
    ;;
esac
