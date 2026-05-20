#!/usr/bin/env bash
# Source this file to load safe defaults for SWE Lite runners.
# This file intentionally does NOT set secrets or provider base URLs.
#
# Usage:
#   source scripts/SWE/openclaw/RTC/setup_swe_env.sh

# Runner defaults
export OPENCLAW_MODEL="${OPENCLAW_MODEL:-deepseek/deepseek-v4-flash}"
export SWE_LITE_INSTANCE_ID="${SWE_LITE_INSTANCE_ID:-pallets__flask-4045}"
export RTC_CACHE_HOME="${RTC_CACHE_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/retrieval-token-cutter}"
export REPO_BASE="${REPO_BASE:-$RTC_CACHE_HOME/swe/openclaw/rtc/cache/repo}"
export SWE_OUTPUT_ROOT="${SWE_OUTPUT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/output_logs}"

# RTC mode local service defaults
export RTC_HTTP_PORT="${RTC_HTTP_PORT:-8090}"
export RTC_URL="${RTC_URL:-http://127.0.0.1:${RTC_HTTP_PORT}}"
export AGFS_BASE_URL="${AGFS_BASE_URL:-http://127.0.0.1:1833}"
export VECTOR_DB_TYPE="${VECTOR_DB_TYPE:-memory}"
export RTC_CODE_TOGGLE_FORCE="${RTC_CODE_TOGGLE_FORCE:-true}"

# Identity defaults for MCP calls
export RTC_ACCOUNT_ID="${RTC_ACCOUNT_ID:-acct-demo}"
export RTC_USER_ID="${RTC_USER_ID:-u-openclaw}"
export RTC_AGENT_ID="${RTC_AGENT_ID:-openclaw-swe}"

# Embedding behavior defaults (no secrets/no base URL values here)
export EMBEDDING_PROVIDER="${EMBEDDING_PROVIDER:-openai}"
export RTC_EMBEDDING_MODEL="${RTC_EMBEDDING_MODEL:-text-embedding-3-large}"

# Indexing/search tuning defaults
export RTC_CODE_SEARCH_CANDIDATE_MAX_FILES="${RTC_CODE_SEARCH_CANDIDATE_MAX_FILES:-40}"
export RTC_CODE_SEARCH_EMBED_MAX_FILES="${RTC_CODE_SEARCH_EMBED_MAX_FILES:-20}"
export RTC_BOOTSTRAP_MAX_FILES="${RTC_BOOTSTRAP_MAX_FILES:-40}"
export RTC_BOOTSTRAP_FULL_INDEX_CAP_FILES="${RTC_BOOTSTRAP_FULL_INDEX_CAP_FILES:-40}"
export RTC_START_LOCAL_EMBED_SERVER="${RTC_START_LOCAL_EMBED_SERVER:-0}"
export SWE_VALIDATION_FORCE_LOCAL="${SWE_VALIDATION_FORCE_LOCAL:-1}"

echo "Loaded scripts/SWE/openclaw SWE defaults."
echo "SWE_LITE_INSTANCE_ID=$SWE_LITE_INSTANCE_ID"
echo "OPENCLAW_MODEL=$OPENCLAW_MODEL"
echo "RTC_URL=$RTC_URL"
echo "EMBEDDING_PROVIDER=$EMBEDDING_PROVIDER"
if [ -n "${RTC_EMBEDDING_API_KEY:-}" ]; then
  echo "RTC_EMBEDDING_API_KEY=set"
else
  echo "RTC_EMBEDDING_API_KEY=<empty> (set this before RTC run)"
fi
