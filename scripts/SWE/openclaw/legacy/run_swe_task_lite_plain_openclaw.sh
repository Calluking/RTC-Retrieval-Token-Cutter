#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RTC_CACHE_HOME="${RTC_CACHE_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/retrieval-token-cutter}"
CACHE_DIR="${SWE_CACHE_DIR:-${RTC_SWE_CACHE_DIR:-$RTC_CACHE_HOME/swe/openclaw/plain/cache}}"
PY_BIN="${PY_BIN:-python3}"
export OPENCLAW_MODEL="${OPENCLAW_MODEL:-deepseek/deepseek-v4-flash}"
export SWE_LITE_INSTANCE_ID="${1:-${SWE_LITE_INSTANCE_ID:-pallets__flask-4045}}"
export SWE_USE_DERIVED_LOCAL_ENV="${SWE_USE_DERIVED_LOCAL_ENV:-1}"
export SWE_VALIDATION_FORCE_LOCAL="${SWE_VALIDATION_FORCE_LOCAL:-1}"
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
    query = urllib.parse.urlencode(
        {
            "dataset": DATASET,
            "config": "default",
            "split": SPLIT,
            "offset": str(offset),
            "length": str(length),
        }
    )
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

Important SWE-bench rule:
- Do not edit benchmark tests, test files, or test fixtures.
- Make the minimal production source-code change needed to satisfy the issue.
- You may run existing tests to reproduce and verify, but the final patch should
  be source-only unless the issue explicitly asks for test changes.
- If the issue text mentions behavior that was already added for a related code
  path, search for that related behavior and keep the public exception semantics
  consistent. Do not use Python `assert` for runtime user-input validation.
- For Flask blueprint dot-name tasks, validate both sides of the issue text:
  dotted blueprint names must raise `ValueError`, and the existing dotted
  endpoint / view-function-name checks must raise `ValueError` too. A patch
  that leaves those endpoint checks as `AssertionError` is incomplete and will
  fail validation; do not preserve that assertion behavior.
"""

prompt_path = os.path.join(repo_base, instance_id, "PROMPT_OPENCLAW_PLAIN.txt")
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
OUTPUT_ROOT="${SWE_OUTPUT_ROOT:-${RTC_SWE_OUTPUT_ROOT:-$SCRIPT_DIR/output_logs}}"
EXPERIMENT_DIR="$OUTPUT_ROOT/${STAMP}-swe-lite-openclaw-plain-r${RUN_IDX}-p$$"
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
- OpenClaw is launched from the SWE task checkout: \`$WORK_DIR\`.
- Make edits for this SWE task in the task checkout: \`$WORK_DIR\`.
EOF2

OPENCLAW_STDOUT="$LOGS_DIR/openclaw-stdout.log"
OPENCLAW_JSON="$LOGS_DIR/openclaw-agent.json"

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
  echo "[setup] Refreshing editable install for current SWE workspace ..." >&2
  if ! (
    cd "$WORK_DIR"
    "$SWE_TASK_ENV_HELPER" --reinstall python - <<'PY'
import sys
print(sys.executable)
PY
  ) >> "$LOCAL_ENV_PREP_LOG" 2>&1; then
    echo "[setup] Failed to refresh current workspace install; see $LOCAL_ENV_PREP_LOG" >&2
    exit 1
  fi
  cat >>"$WORK_DIR/TASK.md" <<EOF2

## Local SWE-bench Environment
- This workspace has a task-specific environment derived from the official SWE-bench \`TestSpec\`.
- Use \`$SWE_TASK_ENV_HELPER\` for reproduction and verification commands.
- Prefer \`./RUN_IN_SWE_LOCAL_ENV.sh pytest -q <target>\`.
- Do not use raw \`python\` or raw \`pytest\` for task verification; those may hit the host interpreter.
EOF2
fi

OPENCLAW_AGENT_ID="${OPENCLAW_AGENT_ID:-swe-openclaw-plain-r${RUN_IDX}-p$$}"
OPENCLAW_SESSION_ID="${OPENCLAW_SESSION_ID:-swe-openclaw-plain-r${RUN_IDX}-p$$}"
OPENCLAW_TIMEOUT="${OPENCLAW_TIMEOUT:-900}"

WORKSPACE_GIT_MOVED=0
OPENCLAW_PLUGINS_BACKUP="$LOGS_DIR/openclaw-plugins-config.before.json"
OPENCLAW_PLUGIN_PATCH="$LOGS_DIR/openclaw-disable-local-plugins.patch.json"

disable_generated_workspace_git() {
  [ "${WORKSPACE_GIT_MOVED:-0}" = "0" ] || return 0
  [ -n "${WORK_DIR:-}" ] || return 0
  [ -n "${EXPERIMENT_DIR:-}" ] || return 0
  if [ -d "$WORK_DIR/.git" ]; then
    rm -rf "$EXPERIMENT_DIR/workspace.git"
    mv "$WORK_DIR/.git" "$EXPERIMENT_DIR/workspace.git"
    cat > "$WORK_DIR/.git-disabled.txt" <<EOF2
Git metadata was moved from workspace/.git to ../workspace.git after this run.
This keeps the generated SWE checkout analyzable while preventing editors from
showing output_logs/workspace as a nested Git repository.
EOF2
    WORKSPACE_GIT_MOVED=1
  fi
}

restore_openclaw_plugin_config() {
  [ -s "$OPENCLAW_PLUGINS_BACKUP" ] || return 0
  "$PY_BIN" - "$OPENCLAW_PLUGINS_BACKUP" "$OPENCLAW_PLUGIN_PATCH" <<'PY'
import json
import sys
from pathlib import Path

plugins = json.loads(Path(sys.argv[1]).read_text())
if "allow" not in plugins:
    plugins["allow"] = None
Path(sys.argv[2]).write_text(json.dumps({"plugins": plugins}, indent=2) + "\n")
PY
  openclaw config patch --file "$OPENCLAW_PLUGIN_PATCH" \
    > "$LOGS_DIR/openclaw-config-restore.log" 2>&1 || true
}

cleanup() {
  restore_openclaw_plugin_config
  disable_generated_workspace_git
}
trap cleanup EXIT

# The user's OpenClaw config may have RTC enabled globally. For the legacy
# runner, isolate the run by temporarily clearing local plugin load paths and
# disabling the RTC entry, then restore the original plugin config on exit.
openclaw config get plugins > "$OPENCLAW_PLUGINS_BACKUP" 2> "$LOGS_DIR/openclaw-config-get-plugins.stderr" || echo '{}' > "$OPENCLAW_PLUGINS_BACKUP"
openclaw config set plugins.load.paths '[]' --strict-json \
  > "$LOGS_DIR/openclaw-config-disable-load-paths.log" 2>&1 || true
openclaw config set plugins.entries.retrieval-token-cutter.enabled false --strict-json \
  > "$LOGS_DIR/openclaw-config-disable-rtc.log" 2>&1 || true
OPENCLAW_MODEL_PROVIDER="${OPENCLAW_MODEL%%/*}"
OPENCLAW_LEGACY_ALLOW_JSON="$("$PY_BIN" - "$OPENCLAW_MODEL_PROVIDER" <<'PY'
import json
import sys
provider = (sys.argv[1] or "").strip()
print(json.dumps([provider] if provider else []))
PY
)"
openclaw config set plugins.allow "$OPENCLAW_LEGACY_ALLOW_JSON" --strict-json \
  > "$LOGS_DIR/openclaw-config-allow-core-provider.log" 2>&1 || true

echo "[setup] Creating OpenClaw agent $OPENCLAW_AGENT_ID for $WORK_DIR" >&2
openclaw agents add "$OPENCLAW_AGENT_ID" \
  --workspace "$WORK_DIR" \
  --model "$OPENCLAW_MODEL" \
  --non-interactive \
  --json > "$LOGS_DIR/openclaw-agent-add.json" 2> "$LOGS_DIR/openclaw-agent-add.stderr" || true

set +e
(
  cd "$WORK_DIR"
  export PYTHONPATH="$WORK_DIR${PYTHONPATH:+:$PYTHONPATH}"
  openclaw agent --local \
    --agent "$OPENCLAW_AGENT_ID" \
    --session-id "$OPENCLAW_SESSION_ID" \
    --model "$OPENCLAW_MODEL" \
    --timeout "$OPENCLAW_TIMEOUT" \
    --message "$(cat "$WORK_DIR/TASK.md")" \
    --json
) 2>&1 | tee "$OPENCLAW_STDOUT" "$OPENCLAW_JSON"
RC=${PIPESTATUS[0]}
set -e

SESSION_JSONL="${HOME}/.openclaw/agents/${OPENCLAW_AGENT_ID}/sessions/${OPENCLAW_SESSION_ID}.jsonl"
SESSION_TRAJECTORY_JSONL="${HOME}/.openclaw/agents/${OPENCLAW_AGENT_ID}/sessions/${OPENCLAW_SESSION_ID}.trajectory.jsonl"
SESSION_TRAJECTORY_PATH_JSON="${HOME}/.openclaw/agents/${OPENCLAW_AGENT_ID}/sessions/${OPENCLAW_SESSION_ID}.trajectory-path.json"
for _jsonl_retry in 1 2 3 4 5; do
  if [ -f "$SESSION_JSONL" ]; then
    break
  fi
  sleep 1
done
if [ -n "$SESSION_JSONL" ] && [ -f "$SESSION_JSONL" ]; then
  cp -f "$SESSION_JSONL" "$LOGS_DIR/"
  [ -f "$SESSION_TRAJECTORY_JSONL" ] && cp -f "$SESSION_TRAJECTORY_JSONL" "$LOGS_DIR/"
  [ -f "$SESSION_TRAJECTORY_PATH_JSON" ] && cp -f "$SESSION_TRAJECTORY_PATH_JSON" "$LOGS_DIR/"
  "$PY_BIN" "$SCRIPT_DIR/render_jsonl_turns.py" "$SESSION_JSONL" > "$EXPERIMENT_DIR/latest_session_render.txt" || true
  "$PY_BIN" - "$SESSION_JSONL" "$EXPERIMENT_DIR/openclaw_tool_summary.json" <<'PY' || true
import json
import sys
from pathlib import Path

session = Path(sys.argv[1])
summary_path = Path(sys.argv[2])
tool_calls = []
tool_results = []
for idx, raw in enumerate(session.read_text(errors="replace").splitlines(), 1):
    try:
        obj = json.loads(raw)
    except Exception:
        continue
    if obj.get("type") != "message":
        continue
    msg = obj.get("message") or {}
    content = msg.get("content") or []
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "toolCall":
                tool_calls.append(
                    {
                        "line": idx,
                        "name": item.get("name"),
                        "arguments": item.get("arguments"),
                    }
                )
    if msg.get("role") == "toolResult":
        tool_results.append(
            {
                "line": idx,
                "name": msg.get("toolName"),
                "isError": msg.get("isError"),
            }
        )

summary = {
    "session_jsonl": str(session),
    "tool_calls": tool_calls,
    "tool_results": tool_results,
    "tool_names": sorted({str(t.get("name")) for t in tool_calls if t.get("name")}),
    "has_rtc_search_code": any(t.get("name") == "rtc_search_code" for t in tool_calls),
    "has_rtc_edit_file": any(t.get("name") == "rtc_edit_file" for t in tool_calls),
    "has_successful_rtc_edit_file": any(
        t.get("name") == "rtc_edit_file" and not t.get("isError") for t in tool_results
    ),
    "used_builtin_edit": any(t.get("name") == "edit" for t in tool_calls),
    "edited_test_file": any(
        t.get("name") in {"rtc_edit_file", "edit", "write", "file_write"}
        and (
            "/test" in str((t.get("arguments") or {}).get("file_path") or (t.get("arguments") or {}).get("path") or "")
            or str((t.get("arguments") or {}).get("file_path") or (t.get("arguments") or {}).get("path") or "").split("/")[-1].startswith("test_")
        )
        for t in tool_calls
    ),
}
summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY
else
  echo "[warn] OpenClaw session JSONL not found: $SESSION_JSONL" >&2
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
  if [ "$VALIDATION_RC" -ne 0 ]; then
    echo "[validate] Validation failed for $SWE_INSTANCE_ID; see $EXPERIMENT_DIR/validation.md" >&2
  fi
fi

disable_generated_workspace_git

echo "Instance: $SWE_INSTANCE_ID ($SWE_REPO @ $SWE_BASE_COMMIT)"
echo "Experiment dir: $EXPERIMENT_DIR"
echo "Workspace: $WORK_DIR"
echo "Logs: $LOGS_DIR"
echo "OpenClaw agent: ${OPENCLAW_AGENT_ID:-<unset>}"
echo "OpenClaw session: ${OPENCLAW_SESSION_ID:-<unset>}"
echo "OpenClaw session jsonl: ${SESSION_JSONL:-<unset>}"
echo "Latest session render: $EXPERIMENT_DIR/latest_session_render.txt"
echo "OpenClaw tool summary: $EXPERIMENT_DIR/openclaw_tool_summary.json"
echo "Validation markdown: $EXPERIMENT_DIR/validation.md"
echo "Validation json: $EXPERIMENT_DIR/validation.json"
echo "Validation rc: $VALIDATION_RC"
if [ "$RC" -ne 0 ]; then
  exit "$RC"
fi
exit "$VALIDATION_RC"
