#!/usr/bin/env bash
set -euo pipefail

# IMPORTANT: OpenClaw must run from the generated SWE workspace, not the
# Retrieval-Token-Cutter repo root. This wrapper delegates to ../RTC, whose
# runner must cd to "$WORK_DIR" before `openclaw agent`/`openclaw chat`;
# otherwise native read/exec tools can resolve paths against the wrong project.

_HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_RTC_RUNNER_DIR="$(cd "$_HERE/../RTC" && pwd)"

RTC_CACHE_HOME="${RTC_CACHE_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/retrieval-token-cutter}"
export SWE_CACHE_DIR="${SWE_CACHE_DIR:-$RTC_CACHE_HOME/swe/openclaw/rtc-filter/cache}"
export SWE_OUTPUT_ROOT="${SWE_OUTPUT_ROOT:-$_HERE/output_logs}"

export RTC_INJECT_FILTERING_PROMPT=1
export RTC_FILTER_ENABLED=1
export RTC_FILTER_NATIVE_READ=1
export RTC_FILTER_NATIVE_BASH=1

exec "$_RTC_RUNNER_DIR/run_swe_task_lite_openclaw_rtc_plugin.sh" "$@"
