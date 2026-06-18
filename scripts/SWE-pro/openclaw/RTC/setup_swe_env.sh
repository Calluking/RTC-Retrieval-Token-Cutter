#!/usr/bin/env bash
# Source this file to load safe defaults for SWE Pro runners.
# This file intentionally does NOT set secrets or provider base URLs.
#
# Usage:
#   source scripts/SWE-pro/openclaw/RTC/setup_swe_env.sh
#
# IMPORTANT: When invoking OpenClaw manually after sourcing this file, cd to the
# generated SWE workspace first. Starting OpenClaw from the RTC repo root makes
# native read/exec tools resolve paths against the wrong project.

# Runner defaults
export OPENCLAW_MODEL="${OPENCLAW_MODEL:-deepseek/deepseek-v4-flash}"
export SWE_PRO_INSTANCE_ID="${SWE_PRO_INSTANCE_ID:-instance_qutebrowser__qutebrowser-f91ace96223cac8161c16dd061907e138fe85111-v059c6fdc75567943479b23ebca7c07b5e9a7f34c}"
export RTC_CACHE_HOME="${RTC_CACHE_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/retrieval-token-cutter}"
export REPO_BASE="${REPO_BASE:-$RTC_CACHE_HOME/swe-pro/openclaw/rtc/cache/repo}"
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
export RTC_EMBEDDING_MODEL="${RTC_EMBEDDING_MODEL:-text-embedding-3-small}"

# Indexing/search tuning defaults
export RTC_CODE_SEARCH_CANDIDATE_MAX_FILES="${RTC_CODE_SEARCH_CANDIDATE_MAX_FILES:-40}"
export RTC_CODE_SEARCH_EMBED_MAX_FILES="${RTC_CODE_SEARCH_EMBED_MAX_FILES:-8}"
export RTC_CODE_SEARCH_MAX_SNIPPETS="${RTC_CODE_SEARCH_MAX_SNIPPETS:-120}"
export RTC_CODE_SEARCH_INGEST_CANDIDATES="${RTC_CODE_SEARCH_INGEST_CANDIDATES:-1}"
export RTC_CODE_SEARCH_INGEST_ASYNC="${RTC_CODE_SEARCH_INGEST_ASYNC:-1}"
export RTC_CODE_SEARCH_INGEST_MAX_FILES="${RTC_CODE_SEARCH_INGEST_MAX_FILES:-3}"
export RTC_CODE_SEARCH_INGEST_MAX_CHUNKS="${RTC_CODE_SEARCH_INGEST_MAX_CHUNKS:-40}"
export RTC_CODE_SEARCH_INGEST_WORKERS="${RTC_CODE_SEARCH_INGEST_WORKERS:-2}"
export RTC_CODE_FUSE_MODE="${RTC_CODE_FUSE_MODE:-weighted_rrf}"
export RTC_CODE_FUSE_W_EMBED="${RTC_CODE_FUSE_W_EMBED:-0.33}"
export RTC_CODE_FUSE_W_BM25="${RTC_CODE_FUSE_W_BM25:-0.17}"
export RTC_CODE_FUSE_W_CTAGS="${RTC_CODE_FUSE_W_CTAGS:-0.17}"
export RTC_CODE_FUSE_W_GRAPH="${RTC_CODE_FUSE_W_GRAPH:-0.33}"
export RTC_SEARCH_LIMIT="${RTC_SEARCH_LIMIT:-5}"
export RTC_BOOTSTRAP_MAX_FILES="${RTC_BOOTSTRAP_MAX_FILES:-40}"
export RTC_BOOTSTRAP_FULL_INDEX_CAP_FILES="${RTC_BOOTSTRAP_FULL_INDEX_CAP_FILES:-40}"
export RTC_START_LOCAL_EMBED_SERVER="${RTC_START_LOCAL_EMBED_SERVER:-0}"
export SWE_VALIDATION_FORCE_LOCAL="${SWE_VALIDATION_FORCE_LOCAL:-1}"
export SWE_SKIP_VALIDATION="${SWE_SKIP_VALIDATION:-1}"

# Plain OpenClaw RTC mode should exercise search/edit only. Read/exec output
# filtering belongs to scripts/SWE-pro/openclaw/RTC-FILTER.
export RTC_INJECT_FILTERING_PROMPT=0
export RTC_FILTER_ENABLED=0
export RTC_FILTER_NATIVE_READ=0
export RTC_FILTER_NATIVE_BASH=0

echo "Loaded scripts/SWE-pro/openclaw SWE defaults."
echo "SWE_PRO_INSTANCE_ID=$SWE_PRO_INSTANCE_ID"
echo "OPENCLAW_MODEL=$OPENCLAW_MODEL"
echo "RTC_URL=$RTC_URL"
echo "EMBEDDING_PROVIDER=$EMBEDDING_PROVIDER"
echo "RTC_SEARCH_LIMIT=$RTC_SEARCH_LIMIT"
echo "SWE_SKIP_VALIDATION=$SWE_SKIP_VALIDATION"
if [ -n "${RTC_EMBEDDING_API_KEY:-}" ]; then
  echo "RTC_EMBEDDING_API_KEY=set"
else
  echo "RTC_EMBEDDING_API_KEY=<empty> (set this before RTC run)"
fi
