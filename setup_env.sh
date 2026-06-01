#!/usr/bin/env bash
# Source this file before starting Claude with the local Retrieval Token Cutter plugin.
#
# Usage:
#   source /path/to/source_tree/setup_env.sh

export RTC_SOURCE_TREE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export RTC_CLAUDE_PLUGIN_DIR="$RTC_SOURCE_TREE/claude-plugin"

# Let developer machines provide local secrets/base URLs from their shell setup.
# This file intentionally does not set API keys.
if [ -f "$HOME/.bashrc" ]; then
  # shellcheck disable=SC1090
  source "$HOME/.bashrc" >/dev/null 2>&1 || true
fi

rtc_python_has_runtime_deps() {
  [ -n "${1:-}" ] || return 1
  [ -x "$1" ] || return 1
  "$1" - <<'PY' >/dev/null 2>&1
import flask
import mcp
import openai
import pyagfs
PY
}

rtc_pick_python() {
  local candidate
  for candidate in \
    "${PY_BIN:-}" \
    "$RTC_SOURCE_TREE/.venv/bin/python" \
    "$RTC_SOURCE_TREE/.venv/bin/python3" \
    "$(command -v python3 2>/dev/null || true)" \
    "$(command -v python 2>/dev/null || true)"
  do
    if rtc_python_has_runtime_deps "$candidate"; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

if ! PY_BIN="$(rtc_pick_python)"; then
  unset PY_BIN
fi
export PY_BIN="${PY_BIN:-}"

export RTC_HTTP_PORT="${RTC_HTTP_PORT:-8090}"
export AGFS_HTTP_PORT="${AGFS_HTTP_PORT:-1833}"
export RTC_URL="${RTC_URL:-http://127.0.0.1:${RTC_HTTP_PORT}}"
export AGFS_BASE_URL="${AGFS_BASE_URL:-http://127.0.0.1:${AGFS_HTTP_PORT}}"
# Local RTC/AGFS traffic must not be routed through HTTP(S)/SOCKS proxies.
export NO_PROXY="127.0.0.1,localhost,::1${NO_PROXY:+,${NO_PROXY}}"
export no_proxy="$NO_PROXY"
export EMBEDDING_PROVIDER="${EMBEDDING_PROVIDER:-openai}"
export RTC_EMBEDDING_BASE_URL="${RTC_EMBEDDING_BASE_URL:-https://api.openai-proxy.org}"
export RTC_EMBEDDING_MODEL="${RTC_EMBEDDING_MODEL:-text-embedding-3-small}"
export RTC_PLUGIN_AUTO_START="${RTC_PLUGIN_AUTO_START:-1}"
export RTC_PLUGIN_AUTO_STOP="${RTC_PLUGIN_AUTO_STOP:-1}"
export RTC_INJECT_FILTERING_PROMPT="${RTC_INJECT_FILTERING_PROMPT:-0}"

echo "Loaded Retrieval Token Cutter Claude plugin defaults."
echo "RTC_CLAUDE_PLUGIN_DIR=$RTC_CLAUDE_PLUGIN_DIR"
echo "PY_BIN=${PY_BIN:-<unset>}"
if [ -z "${PY_BIN:-}" ]; then
  echo "PY_BIN warning: no Python with required runtime packages was found."
  echo "Install with: cd $RTC_SOURCE_TREE && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
fi
if [ -n "${RTC_EMBEDDING_API_KEY:-}" ]; then
  echo "RTC_EMBEDDING_API_KEY=set"
else
  echo "RTC_EMBEDDING_API_KEY=<empty> (set this before real code search)"
fi
