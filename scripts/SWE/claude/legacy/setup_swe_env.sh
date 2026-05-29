#!/usr/bin/env bash
# Source this file to load safe defaults for the plain Claude SWE Lite runner.
#
# IMPORTANT: When invoking the agent manually after sourcing this file, cd to
# the generated SWE workspace first. Starting from the RTC repo root makes
# native file tools resolve paths against the wrong project.

export CLAUDE_MODEL="${CLAUDE_MODEL:-claude-haiku-4-5-20251001}"
export SWE_LITE_INSTANCE_ID="${SWE_LITE_INSTANCE_ID:-pallets__flask-4045}"
export RTC_CACHE_HOME="${RTC_CACHE_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/retrieval-token-cutter}"
export REPO_BASE="${REPO_BASE:-$RTC_CACHE_HOME/swe/plain/cache/repo}"
_SWE_CLAUDE_LEGACY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export SWE_OUTPUT_ROOT="${SWE_OUTPUT_ROOT:-$_SWE_CLAUDE_LEGACY_DIR/output_logs}"
export SWE_VALIDATION_FORCE_LOCAL="${SWE_VALIDATION_FORCE_LOCAL:-1}"

echo "Loaded scripts/SWE/claude/legacy SWE defaults."
echo "SWE_LITE_INSTANCE_ID=$SWE_LITE_INSTANCE_ID"
echo "CLAUDE_MODEL=$CLAUDE_MODEL"
echo "SWE_VALIDATION_FORCE_LOCAL=$SWE_VALIDATION_FORCE_LOCAL"
