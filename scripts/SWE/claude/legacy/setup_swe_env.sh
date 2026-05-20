#!/usr/bin/env bash
# Source this file to load safe defaults for the plain Claude SWE Lite runner.

export CLAUDE_MODEL="${CLAUDE_MODEL:-claude-haiku-4-5-20251001}"
export SWE_LITE_INSTANCE_ID="${SWE_LITE_INSTANCE_ID:-pallets__flask-4045}"
export RTC_CACHE_HOME="${RTC_CACHE_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/retrieval-token-cutter}"
export REPO_BASE="${REPO_BASE:-$RTC_CACHE_HOME/swe/plain/cache/repo}"
export SWE_OUTPUT_ROOT="${SWE_OUTPUT_ROOT:-$RTC_CACHE_HOME/swe/plain/output_logs}"

echo "Loaded scripts/SWE/claude/legacy SWE defaults."
echo "SWE_LITE_INSTANCE_ID=$SWE_LITE_INSTANCE_ID"
echo "CLAUDE_MODEL=$CLAUDE_MODEL"
