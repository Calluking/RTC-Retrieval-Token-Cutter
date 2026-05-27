#!/usr/bin/env bash
# Source this file to load safe defaults for SWE Lite runners.
# This file intentionally does NOT set secrets or provider base URLs.
#
# Usage:
#   source scripts/SWE/claude/RTC/setup_swe_env.sh

# Runner defaults
export CLAUDE_MODEL="${CLAUDE_MODEL:-claude-haiku-4-5-20251001}"
export SWE_LITE_INSTANCE_ID="${SWE_LITE_INSTANCE_ID:-pallets__flask-4045}"
export RTC_CACHE_HOME="${RTC_CACHE_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/retrieval-token-cutter}"
export REPO_BASE="${REPO_BASE:-$RTC_CACHE_HOME/swe/rtc/cache/repo}"
export SWE_OUTPUT_ROOT="${SWE_OUTPUT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/output_logs}"

# RTC mode local service defaults
export RTC_HTTP_PORT="${RTC_HTTP_PORT:-8090}"
export RTC_URL="${RTC_URL:-http://127.0.0.1:${RTC_HTTP_PORT}}"
export AGFS_BASE_URL="${AGFS_BASE_URL:-http://127.0.0.1:1833}"
export VECTOR_DB_TYPE="${VECTOR_DB_TYPE:-memory}"
export RTC_CODE_TOGGLE_FORCE="${RTC_CODE_TOGGLE_FORCE:-true}"

# Identity defaults for MCP calls
export RTC_ACCOUNT_ID="${RTC_ACCOUNT_ID:-acct-demo}"
export RTC_USER_ID="${RTC_USER_ID:-u-claude}"
export RTC_AGENT_ID="${RTC_AGENT_ID:-claude-code}"

# Embedding behavior defaults (no secrets/no base URL values here)
export EMBEDDING_PROVIDER="${EMBEDDING_PROVIDER:-openai}"
export RTC_EMBEDDING_MODEL="${RTC_EMBEDDING_MODEL:-text-embedding-3-small}"

# Indexing/search tuning defaults
export RTC_CODE_SEARCH_CANDIDATE_MAX_FILES="${RTC_CODE_SEARCH_CANDIDATE_MAX_FILES:-80}"
export RTC_CODE_SEARCH_EMBED_MAX_FILES="${RTC_CODE_SEARCH_EMBED_MAX_FILES:-80}"
export RTC_CODE_SEARCH_MAX_SNIPPETS="${RTC_CODE_SEARCH_MAX_SNIPPETS:-500}"
export RTC_CODE_FUSE_MODE="${RTC_CODE_FUSE_MODE:-weighted_rrf}"
export RTC_CODE_FUSE_W_EMBED="${RTC_CODE_FUSE_W_EMBED:-0.33}"
export RTC_CODE_FUSE_W_BM25="${RTC_CODE_FUSE_W_BM25:-0.17}"
export RTC_CODE_FUSE_W_CTAGS="${RTC_CODE_FUSE_W_CTAGS:-0.17}"
export RTC_CODE_FUSE_W_GRAPH="${RTC_CODE_FUSE_W_GRAPH:-0.33}"
export RTC_BOOTSTRAP_MAX_FILES="${RTC_BOOTSTRAP_MAX_FILES:-40}"
export RTC_BOOTSTRAP_FULL_INDEX_CAP_FILES="${RTC_BOOTSTRAP_FULL_INDEX_CAP_FILES:-40}"
export RTC_START_LOCAL_EMBED_SERVER="${RTC_START_LOCAL_EMBED_SERVER:-0}"
export SWE_VALIDATION_FORCE_LOCAL="${SWE_VALIDATION_FORCE_LOCAL:-1}"

echo "Loaded scripts/SWE/claude SWE defaults."
echo "SWE_LITE_INSTANCE_ID=$SWE_LITE_INSTANCE_ID"
echo "CLAUDE_MODEL=$CLAUDE_MODEL"
echo "RTC_URL=$RTC_URL"
echo "EMBEDDING_PROVIDER=$EMBEDDING_PROVIDER"
if [ -n "${RTC_EMBEDDING_API_KEY:-}" ]; then
  echo "RTC_EMBEDDING_API_KEY=set"
else
  echo "RTC_EMBEDDING_API_KEY=<empty> (set this before RTC run)"
fi
