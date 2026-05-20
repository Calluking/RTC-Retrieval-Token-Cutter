#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RTC_CACHE_HOME="${RTC_CACHE_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/retrieval-token-cutter}"
CACHE_DIR="${SWE_CACHE_DIR:-${RTC_SWE_CACHE_DIR:-$RTC_CACHE_HOME/swe/plain/cache}}"
PY_BIN="${PY_BIN:-python3}"
export CLAUDE_MODEL="${CLAUDE_MODEL:-claude-haiku-4-5-20251001}"
export SWE_LITE_INSTANCE_ID="${1:-${SWE_LITE_INSTANCE_ID:-pallets__flask-4045}}"
export SWE_USE_DERIVED_LOCAL_ENV="${SWE_USE_DERIVED_LOCAL_ENV:-1}"
export RUN_IDX="${RUN_IDX:-0}"

REPO_BASE="${REPO_BASE:-$CACHE_DIR/repo}"
mkdir -p "$REPO_BASE"

ensure_python_runtime() {
  if "$PY_BIN" - <<'PY' >/dev/null 2>&1
import json
import urllib.request
PY
  then
    return 0
  fi

  if ! command -v python3 >/dev/null 2>&1; then
    echo "No usable Python interpreter found." >&2
    exit 1
  fi
  PY_BIN="$(command -v python3)"
}

ensure_python_runtime

prompt_exports="$(
  REPO_BASE="$REPO_BASE" "$PY_BIN" - <<'PY'
import json
import os
import sys
import urllib.parse
import urllib.request

DATASET = "princeton-nlp/SWE-bench_Lite"
SPLIT = "test"
BASE = "https://datasets-server.huggingface.co/rows"

target = (os.environ.get("SWE_LITE_INSTANCE_ID") or "").strip()
repo_base = os.environ["REPO_BASE"]
cached_inst_path = os.path.join(repo_base, target, "instance.json") if target else ""

def fetch_rows(offset: int, length: int = 100) -> dict:
    query = urllib.parse.urlencode({
        "dataset": DATASET,
        "config": "default",
        "split": SPLIT,
        "offset": str(offset),
        "length": str(length),
    })
    with urllib.request.urlopen(f"{BASE}?{query}", timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))

def find_row() -> dict:
    if cached_inst_path and os.path.isfile(cached_inst_path):
        with open(cached_inst_path, "r", encoding="utf-8") as f:
            return json.load(f)
    first = fetch_rows(0, 1)
    total = int(first.get("num_rows_total", 0))
    if not target:
        return first["rows"][0]["row"]
    for offset in range(0, max(total, 0), 100):
        block = fetch_rows(offset, 100)
        for item in block.get("rows", []):
            row = item["row"]
            if row.get("instance_id") == target:
                return row
    print(f"No instance_id={target!r} in {SPLIT!r} split of {DATASET} (n={total}).", file=sys.stderr)
    sys.exit(1)

row = find_row()
instance_id = row["instance_id"]
repo = row["repo"]
base_commit = row["base_commit"]
problem = (row.get("problem_statement") or "").strip()
hints = (row.get("hints_text") or "").strip()

instance_path = os.path.join(repo_base, instance_id, "instance.json")
os.makedirs(os.path.dirname(instance_path), exist_ok=True)
with open(instance_path, "w", encoding="utf-8") as f:
    json.dump(row, f, indent=2, ensure_ascii=False)
    f.write("\n")

def esc(value: str) -> str:
    return json.dumps(value)

print(f"export SWE_INSTANCE_ID={esc(instance_id)}")
print(f"export SWE_REPO={esc(repo)}")
print(f"export SWE_BASE_COMMIT={esc(base_commit)}")
print(f"export SWE_INSTANCE_JSON={esc(os.path.abspath(instance_path))}")

prompt = f"""You are working on a real open-source project as in the SWE-bench Lite benchmark.

Repository: {repo}
Checkout: parent commit (state before the fix) is {base_commit}. The codebase is already checked out in this directory.
Do not look up or apply the original solution PR or patch from the web.

Official issue text (`problem_statement`):

---
{problem}
---
"""
if hints:
    prompt += f"""
Optional prior discussion (`hints_text`):
---
{hints}
---
"""
prompt += """
Task:
1. Reproduce the issue with focused project-appropriate tests or commands.
2. Use the failing behavior to locate the best matching implementation site.
3. Fix the bug using the available editing tools.
4. Re-run verification and ensure the relevant tests pass.

Final answer must include:
- root cause
- changed files
- verification command/output
"""

prompt_path = os.path.join(repo_base, instance_id, "PROMPT_PLAIN.txt")
with open(prompt_path, "w", encoding="utf-8") as f:
    f.write(prompt)
print(f"export SWE_PROMPT_FILE={esc(os.path.abspath(prompt_path))}")
PY
)" || {
  echo "[setup] Failed to resolve SWE-bench instance metadata for ${SWE_LITE_INSTANCE_ID:-<unset>}." >&2
  exit 1
}
eval "$prompt_exports"

STAMP="$(date +%Y%m%d-%H%M%S)"
OUTPUT_ROOT="${SWE_OUTPUT_ROOT:-${RTC_SWE_OUTPUT_ROOT:-$RTC_CACHE_HOME/swe/plain/output_logs}}"
EXPERIMENT_DIR="$OUTPUT_ROOT/${STAMP}-swe-lite-plain-r${RUN_IDX}-p$$"
LOGS_DIR="$EXPERIMENT_DIR/logs"
WORK_DIR="$EXPERIMENT_DIR/workspace"
mkdir -p "$LOGS_DIR" "$EXPERIMENT_DIR"
ln -sfn "$EXPERIMENT_DIR" "$OUTPUT_ROOT/latest"

CANON_ROOT="$REPO_BASE/$SWE_INSTANCE_ID"
CANON_DIR="$CANON_ROOT/src"
LOCKS_DIR="$CACHE_DIR/locks"
mkdir -p "$CANON_ROOT" "$LOCKS_DIR"
CANON_LOCK="$LOCKS_DIR/${SWE_INSTANCE_ID}.canon.lock"

{
  flock 9

  canon_repo_ok() {
    [ -d "$1/.git" ] || return 1
    git -C "$1" rev-parse --verify -q HEAD >/dev/null 2>&1 || return 1
    git -C "$1" remote get-url origin >/dev/null 2>&1 || return 1
  }

  if [ -d "$CANON_DIR" ] && ! canon_repo_ok "$CANON_DIR"; then
    echo "[setup] Removing incomplete canonical repo cache: $CANON_DIR" >&2
    rm -rf "$CANON_DIR"
  fi

  if [ ! -d "$CANON_DIR/.git" ]; then
    tmp_dir="${CANON_DIR}.tmp.$$"
    rm -rf "$tmp_dir"
    echo "Cloning https://github.com/${SWE_REPO}.git ..." >&2
    git clone "https://github.com/${SWE_REPO}.git" "$tmp_dir"
    if ! canon_repo_ok "$tmp_dir"; then
      echo "[setup] Canonical repo clone did not produce a valid HEAD: $tmp_dir" >&2
      rm -rf "$tmp_dir"
      exit 1
    fi
    mv "$tmp_dir" "$CANON_DIR"
  fi

  git -C "$CANON_DIR" fetch --all --prune
  if ! git -C "$CANON_DIR" rev-parse --verify -q "$SWE_BASE_COMMIT^{commit}" >/dev/null 2>&1; then
    git -C "$CANON_DIR" fetch origin
  fi
  git -C "$CANON_DIR" checkout -f "$SWE_BASE_COMMIT" --
  git -C "$CANON_DIR" clean -fdx

  rm -rf "$WORK_DIR"
  git clone --quiet "$CANON_DIR" "$WORK_DIR"
} 9>"$CANON_LOCK"

cp -a "$SWE_INSTANCE_JSON" "$EXPERIMENT_DIR/instance.json"
cp -a "$SWE_PROMPT_FILE" "$WORK_DIR/TASK.md"
cat >>"$WORK_DIR/TASK.md" <<EOF2

## Workspace
- Claude is launched from the SWE task checkout: \`$WORK_DIR\`.
- Make edits for this SWE task in the task checkout: \`$WORK_DIR\`.
EOF2

CLAUDE_LOG="$LOGS_DIR/claude-code-debug.log"
CLAUDE_STDOUT="$LOGS_DIR/claude-stdout.log"
export CLAUDE_CODE_DEBUG_LOGS_DIR="${CLAUDE_CODE_DEBUG_LOGS_DIR:-$LOGS_DIR}"
export CLAUDE_CODE_DEBUG_LOG_LEVEL="${CLAUDE_CODE_DEBUG_LOG_LEVEL:-debug}"

if [ "$SWE_USE_DERIVED_LOCAL_ENV" = "1" ]; then
  echo "[setup] Deriving local SWE-bench env ..." >&2
  LOCAL_ENV_PREP_LOG="$LOGS_DIR/swe-local-env-prepare.log"
  LOCAL_ENV_EXPORTS_FILE="$LOGS_DIR/swe-local-env-exports.sh"
  if ! "$PY_BIN" "$SCRIPT_DIR/prepare_swe_local_env.py" "$SWE_INSTANCE_JSON" "$WORK_DIR" "$EXPERIMENT_DIR" \
      > "$LOCAL_ENV_EXPORTS_FILE" 2>> "$LOCAL_ENV_PREP_LOG"; then
    cat "$LOCAL_ENV_EXPORTS_FILE" >> "$LOCAL_ENV_PREP_LOG" 2>/dev/null || true
    echo "[setup] Failed to derive local SWE-bench env; see $LOCAL_ENV_PREP_LOG" >&2
    exit 1
  fi
  cat "$LOCAL_ENV_EXPORTS_FILE" >> "$LOCAL_ENV_PREP_LOG"
  local_env_exports="$(grep '^export ' "$LOCAL_ENV_EXPORTS_FILE" || true)"
  if [ -z "$local_env_exports" ]; then
    echo "[setup] Local SWE-bench env derivation produced no exports; see $LOCAL_ENV_PREP_LOG" >&2
    exit 1
  fi
  eval "$local_env_exports"
  cat >>"$WORK_DIR/TASK.md" <<EOF2

## Local SWE-bench Environment
- Use \`$SWE_TASK_ENV_HELPER\` for reproduction and verification commands.
- Prefer \`./RUN_IN_SWE_LOCAL_ENV.sh pytest -q <target>\`.
- Do not use raw \`python\` or raw \`pytest\` for task verification; those may hit the host interpreter.
EOF2
fi

set +e
(
  cd "$WORK_DIR"
  export PYTHONPATH="$WORK_DIR${PYTHONPATH:+:$PYTHONPATH}"
  claude --model "$CLAUDE_MODEL" \
    --dangerously-skip-permissions \
    --permission-mode bypassPermissions \
    --print --debug-file "$CLAUDE_LOG" < "$WORK_DIR/TASK.md"
) 2>&1 | tee "$CLAUDE_STDOUT"
RC=${PIPESTATUS[0]}
set -e

WORK_SLUG="$("$PY_BIN" - "$WORK_DIR" <<'PY'
import re
import sys
print(re.sub(r'[^A-Za-z0-9]+', '-', sys.argv[1]).rstrip('-'))
PY
)"
PROJ_DIR="${HOME}/.claude/projects/${WORK_SLUG}"
SESSION_JSONL=""
for _jsonl_retry in 1 2 3 4 5; do
  if [ -d "$PROJ_DIR" ]; then
    SESSION_JSONL="$(find "$PROJ_DIR" -maxdepth 1 -type f -name '*.jsonl' | sort | tail -n 1 || true)"
  fi
  if [ -n "$SESSION_JSONL" ] && [ -f "$SESSION_JSONL" ]; then
    break
  fi
  sleep 1
done
if [ -n "$SESSION_JSONL" ] && [ -f "$SESSION_JSONL" ]; then
  cp -f "$SESSION_JSONL" "$LOGS_DIR/"
  "$PY_BIN" "$SCRIPT_DIR/render_jsonl_turns.py" "$SESSION_JSONL" > "$EXPERIMENT_DIR/latest_session_render.txt" || true
fi

VALIDATION_RC=0
if [ "${SWE_SKIP_VALIDATION:-0}" = "1" ]; then
  echo "[validate] Skipped validation for $SWE_INSTANCE_ID (SWE_SKIP_VALIDATION=1)." >&2
  "$PY_BIN" - "$SWE_INSTANCE_ID" "$EXPERIMENT_DIR" <<'PY'
import json
import sys
from pathlib import Path

instance_id, exp_dir = sys.argv[1], Path(sys.argv[2])
payload = {
    "instance_id": instance_id,
    "status": "skipped",
    "validation_mode": "skipped",
    "reason": "SWE_SKIP_VALIDATION=1",
}
(exp_dir / "validation.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
(exp_dir / "validation.md").write_text("# Validation skipped\n\nSWE_SKIP_VALIDATION=1\n", encoding="utf-8")
PY
else
  echo "[validate] Starting attached validation for $SWE_INSTANCE_ID ..." >&2
  set +e
  "$PY_BIN" "$SCRIPT_DIR/validate_swe_run.py" "$SWE_INSTANCE_JSON" "$WORK_DIR" "$EXPERIMENT_DIR" \
    > "$LOGS_DIR/validation-summary.json" 2> "$LOGS_DIR/validation-stderr.log"
  VALIDATION_RC=$?
  set -e
fi

echo "Instance: $SWE_INSTANCE_ID ($SWE_REPO @ $SWE_BASE_COMMIT)"
echo "Experiment dir: $EXPERIMENT_DIR"
echo "Workspace: $WORK_DIR"
echo "Logs: $LOGS_DIR"
echo "Validation markdown: $EXPERIMENT_DIR/validation.md"
echo "Validation json: $EXPERIMENT_DIR/validation.json"
echo "Validation rc: $VALIDATION_RC"
if [ "$RC" -ne 0 ]; then
  exit "$RC"
fi
exit "$VALIDATION_RC"
