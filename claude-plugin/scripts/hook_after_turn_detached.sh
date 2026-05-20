#!/usr/bin/env bash
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$HERE/hook_after_turn.py"
PYTHON_BIN="${PY_BIN:-python3}"
INPUT="$(cat)"
TMPFILE="$(mktemp)"
printf '%s' "$INPUT" >"$TMPFILE"

setsid bash -c '"$1" "$2" <"$3"; rm -f "$3"' _ "$PYTHON_BIN" "$SCRIPT" "$TMPFILE" </dev/null >/dev/null 2>&1 &
disown 2>/dev/null || true

exit 0
