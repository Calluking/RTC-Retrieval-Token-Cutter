"""MCP stdio server exposing Retrieval Token Cutter code search for the Claude Code plugin."""

from __future__ import annotations

import atexit
import json
import os
import re
import signal
import subprocess
import sys
from pathlib import Path
from typing import Annotated
import urllib.request

from mcp.server.fastmcp import FastMCP

from retrieval_token_cutter_mcp.http_client import identity_fields, post_json

app = FastMCP("retrieval-token-cutter")

_IDENT = r"[A-Za-z_][A-Za-z0-9_]*"
_STARTED_BACKEND = False


def _plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _backend_healthy() -> bool:
    url = (os.environ.get("RTC_URL") or "http://127.0.0.1:8090").rstrip("/") + "/api/v1/health"
    try:
        with urllib.request.urlopen(url, timeout=2):
            return True
    except Exception:
        return False


def _start_backend_if_needed() -> None:
    global _STARTED_BACKEND
    if os.environ.get("RTC_PLUGIN_AUTO_START", "1") == "0":
        return
    if _backend_healthy():
        return
    _STARTED_BACKEND = True
    plugin = _plugin_root()
    env = os.environ.copy()
    env.setdefault("PY_BIN", sys.executable)
    wait = os.environ.get("RTC_PLUGIN_START_WAIT", "45")
    subprocess.Popen(
        [sys.executable, str(plugin / "scripts" / "rtc_terminal.py"), "start", "--wait", wait],
        cwd=str(plugin.parent),
        env=env,
        stdout=sys.stderr,
        stderr=sys.stderr,
        start_new_session=True,
    )


def _stop_backend_if_owned() -> None:
    if not _STARTED_BACKEND or os.environ.get("RTC_PLUGIN_AUTO_STOP", "1") == "0":
        return
    plugin = _plugin_root()
    try:
        subprocess.run(
            [sys.executable, str(plugin / "scripts" / "rtc_terminal.py"), "stop"],
            cwd=str(plugin.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except Exception:
        pass


def _handle_signal(signum: int, _frame: object) -> None:
    _stop_backend_if_owned()
    raise SystemExit(128 + signum)


_start_backend_if_needed()
atexit.register(_stop_backend_if_owned)
for _sig in (signal.SIGTERM, signal.SIGINT):
    signal.signal(_sig, _handle_signal)


def _canonical_code_query(query: str) -> str:
    q = (query or "").strip()
    if not q:
        return q

    patterns = (
        (rf"^function\s+({_IDENT})$", "{symbol} function"),
        (rf"^def\s+({_IDENT})$", "{symbol} function"),
        (rf"^async\s+function\s+({_IDENT})$", "{symbol} async function"),
        (rf"^async\s+def\s+({_IDENT})$", "{symbol} async function"),
        (rf"^type\s+({_IDENT})$", "{symbol} type"),
    )
    for pattern, template in patterns:
        match = re.match(pattern, q, flags=re.IGNORECASE)
        if match:
            return template.format(symbol=match.group(1))
    return q


def _workspace_root_arg(path: str | None) -> str | None:
    raw = (path or "").strip()
    unresolved = {
        "",
        "$WORK_DIR",
        "${WORK_DIR}",
        "$PWD",
        "${PWD}",
        "$RTC_WORKSPACE_ROOT",
        "${RTC_WORKSPACE_ROOT}",
    }
    if raw in unresolved:
        raw = os.environ.get("RTC_WORKSPACE_ROOT", "") or os.environ.get("CLAUDE_PROJECT_DIR", "") or os.getcwd()
    if not raw:
        return None
    return str(Path(os.path.expandvars(raw)).expanduser().resolve())


def _resolve_workspace_path(workspace_root: str, file_path: str) -> Path:
    root = Path(workspace_root).expanduser().resolve()
    target = Path(file_path).expanduser()
    target = target if target.is_absolute() else (root / target)
    target = target.resolve()
    target.relative_to(root)
    return target


def _effective_search_limit(requested_limit: int) -> int:
    forced_raw = (os.environ.get("RTC_SEARCH_FORCE_LIMIT") or "").strip()
    if forced_raw:
        try:
            return max(1, min(100, int(forced_raw)))
        except ValueError:
            pass
    return int(requested_limit)


@app.tool(
    description="""\
Index a workspace directory so code-mode semantic search can use Retrieval Token Cutter vectors.

`path` should be an absolute workspace root. This maps to
`POST /api/v1/code_workspace_bootstrap`.

Use this only when you need to explicitly warm/index a tree. Normal
`search_code` calls perform candidate indexing automatically.
""",
)
def index_codebase(
    path: Annotated[str, "Absolute path to the workspace directory to index."],
    force: Annotated[bool, "Reserved; re-index override (currently ignored)."] = False,
) -> str:
    return json.dumps(
        {
            "ok": True,
            "skipped": True,
            "reason": "search_code performs candidate indexing automatically",
            "workspace_root": _workspace_root_arg(path),
            "force": force,
            "next_step": "Call search_code with a focused query.",
        },
        indent=2,
    )


@app.tool(
    description="""\
Search indexed code memories using a natural language query.

Returns raw backend hits, especially `content_excerpt` values with
`# repo/path (lines start-end)` headers.

MCP requirement: before editing source/code files, call this tool at least
once with a focused query. Treat this as the preferred replacement for broad
grep and exploratory Read. Use 1-2 focused symbol-level searches when possible.
If snippets already identify the target file and line context, proceed directly
to `mcp__plugin_retrieval-token-cutter_retrieval-token-cutter__edit_file` or the next concrete verification step instead
of reading many unrelated files.
""",
)
def search_code(
    query: Annotated[str, "Natural language or keyword query."],
    path: Annotated[str, "Workspace root. Leave empty to use RTC_WORKSPACE_ROOT, then Claude's launch/project directory."] = "",
    limit: Annotated[int, "Max hits (1-100)."] = 5,
    glob_patterns: Annotated[str, "Optional comma-separated glob patterns to narrow candidate files before ranking."] = "",
    grep_terms: Annotated[str, "Optional comma-separated grep keywords/symbols to narrow candidate files before ranking."] = "",
) -> str:
    body = identity_fields(
        {
            "workspaceRoot": _workspace_root_arg(path),
            "query": _canonical_code_query(query),
            "limit": _effective_search_limit(limit),
            "glob_patterns": glob_patterns or None,
            "grep_terms": grep_terms or None,
            "waitForFullWorkspaceIndex": False,
        }
    )
    result = post_json("/api/v1/call/code_semantic_search", body)
    return json.dumps(result, indent=2)


@app.tool(
    description="""\
Edit a file via exact string replacement without requiring a prior Read tool call.

This is an MCP replacement for Claude's built-in Edit tool:
- validates the target is under `workspace_root`
- replaces `old_string` with `new_string`
- can replace once or all matches

Use this for source/code edits after locating the relevant file with
`mcp__plugin_retrieval-token-cutter_retrieval-token-cutter__search_code`. Prefer it over Claude's built-in Edit tool for
files found through Retrieval Token Cutter.
""",
)
def edit_file(
    file_path: Annotated[str, "Absolute or workspace-relative target file path."],
    old_string: Annotated[str, "Exact text to replace."],
    new_string: Annotated[str, "Replacement text."],
    workspace_root: Annotated[str, "Workspace root used to validate the target path. Leave empty to use RTC_WORKSPACE_ROOT, then Claude's launch/project directory."] = "",
    replace_all: Annotated[bool, "Replace every occurrence instead of exactly one."] = False,
) -> str:
    root = _workspace_root_arg(workspace_root) or str(Path.cwd())
    target = _resolve_workspace_path(root, file_path)
    if not target.exists():
        raise FileNotFoundError(f"Target file not found: {target}")
    original = target.read_text(encoding="utf-8")
    if old_string not in original:
        raise ValueError("old_string not found in target file")

    occurrences = original.count(old_string)
    if not replace_all and occurrences != 1:
        raise ValueError(
            f"old_string matched {occurrences} times; pass replace_all=true or provide a more specific old_string"
        )

    updated = original.replace(old_string, new_string) if replace_all else original.replace(old_string, new_string, 1)
    target.write_text(updated, encoding="utf-8")

    refresh_wait = (os.environ.get("RTC_EDIT_REFRESH_WAIT") or "0").strip().lower() in {"1", "true", "yes", "on"}
    try:
        refresh_timeout_sec = max(1.0, float(os.environ.get("RTC_EDIT_REFRESH_TIMEOUT_SEC") or "5"))
    except ValueError:
        refresh_timeout_sec = 5.0

    refresh_body = identity_fields(
        {
            "workspaceRoot": str(Path(root).expanduser().resolve()),
            "file_path": str(target),
            "wait_for_index": refresh_wait,
            "refresh_timeout_sec": refresh_timeout_sec,
        }
    )
    try:
        refresh = post_json(
            "/api/v1/call/code_refresh_workspace_path",
            refresh_body,
            timeout_sec=refresh_timeout_sec + 1.0,
        )
    except Exception as exc:
        refresh = {"ok": False, "background_refresh_dispatched": False, "error": str(exc)}

    return json.dumps(
        {
            "ok": True,
            "file_path": str(target),
            "relative_path": target.relative_to(Path(root).expanduser().resolve()).as_posix(),
            "replace_all": replace_all,
            "occurrences": occurrences,
            "bytes_before": len(original.encode("utf-8")),
            "bytes_after": len(updated.encode("utf-8")),
            "memory_refresh": refresh,
        },
        indent=2,
    )


def main() -> None:
    app.run(transport="stdio")
