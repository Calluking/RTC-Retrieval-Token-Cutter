#!/usr/bin/env bash
# Source this file to load safe defaults for the OpenClaw RTC-FILTER SWE Pro runner.
# This file intentionally does NOT set secrets or provider base URLs.
#
# Usage:
#   source scripts/SWE-pro/openclaw/RTC-FILTER/setup_swe_env.sh
#
# IMPORTANT: When invoking OpenClaw manually after sourcing this file, cd to the
# generated SWE workspace first. Starting OpenClaw from the RTC repo root makes
# native read/exec tools resolve paths against the wrong project.

_HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RTC_CACHE_HOME="${RTC_CACHE_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/retrieval-token-cutter}"

export SWE_CACHE_DIR="${SWE_CACHE_DIR:-$RTC_CACHE_HOME/swe-pro/openclaw/rtc-filter/cache}"
export REPO_BASE="${REPO_BASE:-$SWE_CACHE_DIR/repo}"
export SWE_OUTPUT_ROOT="${SWE_OUTPUT_ROOT:-$_HERE/output_logs}"

export RTC_INJECT_FILTERING_PROMPT=1
export RTC_FILTER_ENABLED=1
export RTC_FILTER_NATIVE_READ=1
export RTC_FILTER_NATIVE_BASH=1

# Reuse the OpenClaw RTC defaults after setting this mode's cache/output roots.
# shellcheck disable=SC1091
source "$_HERE/../RTC/setup_swe_env.sh"

echo "Loaded scripts/SWE-pro/openclaw RTC-FILTER defaults."
echo "SWE_OUTPUT_ROOT=$SWE_OUTPUT_ROOT"
echo "SWE_CACHE_DIR=$SWE_CACHE_DIR"
echo "RTC_INJECT_FILTERING_PROMPT=$RTC_INJECT_FILTERING_PROMPT"
echo "RTC_FILTER_ENABLED=$RTC_FILTER_ENABLED"
echo "RTC_FILTER_NATIVE_READ=$RTC_FILTER_NATIVE_READ"
echo "RTC_FILTER_NATIVE_BASH=$RTC_FILTER_NATIVE_BASH"
