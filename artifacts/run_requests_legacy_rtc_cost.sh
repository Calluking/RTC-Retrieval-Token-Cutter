#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/luzh22/og-enhance/20260513/swe_lite_og_dev2_slimdown/source_tree"
LEGACY_RUNNER="$ROOT/scripts/SWE/claude/legacy/run_swe_task_lite_plain_claude.sh"
RTC_RUNNER="$ROOT/scripts/SWE/claude/RTC/run_swe_task_lite_rtc_plugin.sh"
LEGACY_OUT="$ROOT/scripts/SWE/claude/legacy/output_logs/20260524-requests-legacy-cost"
RTC_OUT="$ROOT/scripts/SWE/claude/RTC/output_logs/20260524-requests-current-rtc-cost"

TASKS=(
  psf__requests-1963
  psf__requests-2148
  psf__requests-2317
  psf__requests-2674
  psf__requests-3362
)

summarize() {
  local run_dir="$1"
  python3 - "$run_dir" <<'PY'
import json
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
seen = set()
totals = {
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_read_input_tokens": 0,
    "cache_creation_input_tokens": 0,
    "cache_creation_input_tokens_5m": 0,
    "cache_creation_input_tokens_1h": 0,
}

def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk(value)

def usage_id(event, path, line_no):
    request_id = event.get("requestId") or event.get("request_id")
    if request_id:
        return (path.name, request_id)
    msg = event.get("message")
    if isinstance(msg, dict) and msg.get("id"):
        return (path.name, msg["id"])
    return (path.name, line_no)

jsonls = sorted(run_dir.glob("logs/*.jsonl")) + sorted(run_dir.glob("*.jsonl"))
for path in jsonls:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        continue
    for line_no, line in enumerate(lines, 1):
        try:
            event = json.loads(line)
        except Exception:
            continue
        found_usage = False
        for obj in walk(event):
            usage = obj.get("usage")
            if not isinstance(usage, dict):
                continue
            if not any(k in usage for k in totals):
                continue
            found_usage = True
            key = usage_id(event, path, line_no)
            if key in seen:
                continue
            seen.add(key)
            for name in totals:
                totals[name] += int(usage.get(name) or 0)
            break

input_tokens = totals["input_tokens"]
output_tokens = totals["output_tokens"]
cache_read = totals["cache_read_input_tokens"]
cache_create = totals["cache_creation_input_tokens"]
cache_create_5m = totals["cache_creation_input_tokens_5m"]
cache_create_1h = totals["cache_creation_input_tokens_1h"]
if cache_create and not (cache_create_5m or cache_create_1h):
    cache_create_5m = cache_create

cost = (
    input_tokens / 1_000_000 * 1.00
    + output_tokens / 1_000_000 * 5.00
    + cache_read / 1_000_000 * 0.10
    + cache_create_5m / 1_000_000 * 1.25
    + cache_create_1h / 1_000_000 * 2.00
)
print(json.dumps({
    "input": input_tokens,
    "output": output_tokens,
    "cache_read": cache_read,
    "cache_create_5m": cache_create_5m,
    "cache_create_1h": cache_create_1h,
    "total_tokens": input_tokens + output_tokens + cache_read + cache_create_5m + cache_create_1h,
    "cost": round(cost, 6),
}, sort_keys=True))
PY
}

run_one() {
  local kind="$1"
  local task="$2"
  local idx="$3"
  local runner out_dir
  if [ "$kind" = "legacy" ]; then
    runner="$LEGACY_RUNNER"
    out_dir="$LEGACY_OUT"
  else
    runner="$RTC_RUNNER"
    out_dir="$RTC_OUT"
  fi
  mkdir -p "$out_dir"
  echo "===== ${kind^^} $task ====="
  set +e
  SWE_SKIP_VALIDATION=1 SWE_OUTPUT_ROOT="$out_dir" RTC_SWE_OUTPUT_ROOT="$out_dir" RUN_IDX="$idx" "$runner" "$task"
  local rc=$?
  set -e
  local latest
  latest="$(readlink -f "$out_dir/latest" 2>/dev/null || true)"
  local metrics="{}"
  if [ -n "$latest" ] && [ -d "$latest" ]; then
    metrics="$(summarize "$latest")"
  fi
  printf 'SUMMARY\t%s\t%s\trc=%s\trun=%s\tmetrics=%s\n' "$kind" "$task" "$rc" "${latest:-<missing>}" "$metrics"
}

echo -e "kind\ttask\trc\trun_dir\tmetrics"
for i in "${!TASKS[@]}"; do
  task="${TASKS[$i]}"
  run_one legacy "$task" "$((700 + i))"
  run_one rtc "$task" "$((800 + i))"
done
