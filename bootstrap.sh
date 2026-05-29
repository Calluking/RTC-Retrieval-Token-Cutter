#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
VENV_DIR="$ROOT_DIR/.venv"
FORCE_AGFS=0
SKIP_PYTHON=0
SKIP_AGFS=0
INSTALL_OPENCLAW=0

usage() {
  cat <<'EOF'
Usage: ./bootstrap.sh [options]

Prepare a fresh Retrieval Token Cutter checkout for local Claude/OpenClaw use.

Options:
  --force-agfs              Rebuild agfs/build/agfs-server even if it exists.
  --skip-python             Do not create .venv or install requirements.txt.
  --skip-agfs               Do not build the bundled AGFS server.
  --install-openclaw-plugin Install and enable the linked OpenClaw plugin.
  -h, --help                Show this help.

The script creates env.sh from env.sh.example if env.sh does not exist.
You still need to edit env.sh and set RTC_EMBEDDING_API_KEY before real code search.
EOF
}

log() {
  printf '[bootstrap] %s\n' "$*"
}

die() {
  printf '[bootstrap] error: %s\n' "$*" >&2
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --force-agfs)
      FORCE_AGFS=1
      ;;
    --skip-python)
      SKIP_PYTHON=1
      ;;
    --skip-agfs)
      SKIP_AGFS=1
      ;;
    --install-openclaw-plugin)
      INSTALL_OPENCLAW=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown option: $1"
      ;;
  esac
  shift
done

cd "$ROOT_DIR"
log "repository: $ROOT_DIR"

if [ "$SKIP_PYTHON" -eq 0 ]; then
  command -v "$PYTHON_BIN" >/dev/null 2>&1 || die "missing Python: $PYTHON_BIN"
  if [ ! -d "$VENV_DIR" ]; then
    log "creating Python virtual environment at .venv"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  else
    log "using existing .venv"
  fi

  log "installing Python dependencies from requirements.txt"
  "$VENV_DIR/bin/python" -m pip install --upgrade pip
  "$VENV_DIR/bin/python" -m pip install -r "$ROOT_DIR/requirements.txt"
else
  log "skipping Python dependency setup"
fi

if [ ! -f "$ROOT_DIR/env.sh" ]; then
  log "creating env.sh from env.sh.example"
  cp "$ROOT_DIR/env.sh.example" "$ROOT_DIR/env.sh"
else
  log "env.sh already exists"
fi

AGFS_BIN="$ROOT_DIR/agfs/build/agfs-server"
if [ "$SKIP_AGFS" -eq 0 ]; then
  if [ "$FORCE_AGFS" -eq 1 ] || [ ! -x "$AGFS_BIN" ]; then
    command -v make >/dev/null 2>&1 || die "missing make; install make or rerun with --skip-agfs"
    command -v go >/dev/null 2>&1 || die "missing Go; install Go 1.21+ or rerun with --skip-agfs"
    log "building bundled AGFS server"
    make -C "$ROOT_DIR/agfs" build
  else
    log "AGFS server already built at agfs/build/agfs-server"
  fi
else
  log "skipping AGFS build"
fi

if [ "$INSTALL_OPENCLAW" -eq 1 ]; then
  command -v openclaw >/dev/null 2>&1 || die "missing openclaw CLI"
  log "installing linked OpenClaw plugin"
  openclaw plugins install --link "$ROOT_DIR/openclaw-plugin" --dangerously-force-unsafe-install
  openclaw plugins enable retrieval-token-cutter
  openclaw gateway restart
fi

cat <<EOF

Bootstrap complete.

Next:
  1. Edit env.sh and set RTC_EMBEDDING_API_KEY.
  2. Start Claude from a target project:
     $ROOT_DIR/claude-plugin/bin/rtc-claude
  3. Or install OpenClaw once:
     ./bootstrap.sh --install-openclaw-plugin

EOF
