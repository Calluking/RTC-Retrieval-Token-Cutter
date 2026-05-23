#!/usr/bin/env python3
"""Terminal and hook entrypoints for the Retrieval Token Cutter Claude plugin."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_URL = "http://127.0.0.1:8090"
SIDE_EFFECT_TOOLS = {"Write", "Edit", "MultiEdit", "Bash", "NotebookEdit"}
MAX_TOOL_CHARS = 10000
PLUGIN_ROOT = Path(__file__).resolve().parents[1]
CODE_POLICY_PROMPT_PATH = PLUGIN_ROOT / "prompts" / "code_policy_injection.txt"


def log(prefix: str, message: str) -> None:
    print(f"[{prefix}] {message}", file=sys.stderr)


def api_url() -> str:
    return (os.environ.get("RTC_URL") or DEFAULT_URL).rstrip("/")


def identity(session_id: str | None = None) -> dict[str, str]:
    out = {
        "accountId": os.environ.get("RTC_ACCOUNT_ID")
        or os.environ.get("RTC_ACCOUNT_ID", "acct-demo"),
        "userId": os.environ.get("RTC_USER_ID")
        or os.environ.get("RTC_USER_ID", "u-claude"),
        "agentId": os.environ.get("RTC_AGENT_ID")
        or os.environ.get("RTC_AGENT_ID", "claude-code"),
    }
    sid = session_id or os.environ.get("RTC_SESSION_ID")
    if sid:
        out["sessionId"] = sid
    return out


def headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    key = (os.environ.get("RTC_AUTH_API_KEY") or "").strip()
    if key:
        h["X-API-Key"] = key
        h["X-Account-ID"] = identity().get("accountId", "acct-demo")
        h["X-User-ID"] = identity().get("userId", "u-claude")
    return h


def post_json(path: str, body: dict[str, Any], timeout: float = 30.0) -> dict[str, Any]:
    url = api_url() + path
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers=headers(), method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw) if raw.strip() else {}


def get_json(path: str, timeout: float = 10.0) -> dict[str, Any]:
    req = urllib.request.Request(api_url() + path, headers=headers(), method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw) if raw.strip() else {}


def compact_json(obj: Any, limit: int = MAX_TOOL_CHARS) -> str:
    try:
        text = json.dumps(obj, ensure_ascii=False, default=str)
    except TypeError:
        text = str(obj)
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [{len(text) - limit} more chars omitted]"


def looks_like_code_prompt(prompt: str) -> bool:
    lowered = prompt.lower()
    keywords = (
        "bug",
        "fix",
        "test",
        "function",
        "class",
        "method",
        "source",
        "code",
        "repo",
        "implementation",
        "traceback",
        "error",
    )
    return any(keyword in lowered for keyword in keywords)


def code_policy_prompt() -> str:
    try:
        return CODE_POLICY_PROMPT_PATH.read_text(encoding="utf-8").strip()
    except OSError as exc:
        log("call_compose", f"failed to read code policy injection: {exc}")
        return ""


def extract_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
        return "\n".join(parts).strip()
    return ""


def parse_transcript_chunk(text: str) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("isSidechain") or entry.get("isApiErrorMessage"):
            continue
        if entry.get("type") not in {"user", "assistant"}:
            continue
        msg = entry.get("message")
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        if role not in {"user", "assistant"}:
            continue
        content = extract_text(msg.get("content", ""))
        if content:
            messages.append({"role": role, "content": content})
    return messages


def project_transcript_dir(project_dir: str | None = None) -> Path:
    cwd = Path(project_dir or os.getcwd()).resolve()
    slug = str(cwd).replace("/", "-").replace("_", "-")
    candidates = [
        Path.home() / ".claude" / "projects" / slug,
        Path.home() / ".claude" / "projects" / f"-{slug}",
    ]
    for path in candidates:
        if path.is_dir():
            return path
    return candidates[0]


def format_compose(data: dict[str, Any]) -> str:
    sections = [
        ("identityContext", "Profile"),
        ("episodicContext", "Archives"),
        ("sessionContext", "Session"),
        ("retrievedEvidence", "Working Set"),
        ("memoryUserMessage", "Memory Message"),
    ]
    parts = []
    for key, label in sections:
        value = str(data.get(key) or "").strip()
        if value:
            parts.append(f"## {label}\n{value}")
    return "\n\n".join(parts) if parts else "No relevant context found."


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def repo_root_from_plugin() -> Path:
    return plugin_root().parent


def runtime_dir(args: argparse.Namespace | None = None) -> Path:
    raw = getattr(args, "runtime_dir", None) if args else None
    raw = raw or os.environ.get("RTC_RUNTIME_DIR")
    if raw:
        return Path(raw).expanduser().resolve()
    return Path.home() / ".cache" / "retrieval-token-cutter-claude-plugin"


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def read_pid(path: Path) -> int | None:
    try:
        return int(path.read_text().strip())
    except Exception:
        return None


def find_agfs_bin(repo_root: Path) -> str:
    env_bin = os.environ.get("AGFS_BIN")
    if env_bin and Path(env_bin).expanduser().is_file():
        return str(Path(env_bin).expanduser().resolve())
    local = repo_root / "agfs" / "build" / "agfs-server"
    if local.is_file() and os.access(local, os.X_OK):
        return str(local)
    found = shutil.which("agfs-server")
    if found:
        return found
    raise RuntimeError("agfs-server not found. Set AGFS_BIN or put agfs-server on PATH.")


def write_agfs_config(path: Path, data_dir: Path, port: int) -> None:
    path.write_text(
        "\n".join(
            [
                "server:",
                f'  address: ":{port}"',
                "  log_level: info",
                "plugins:",
                "  serverinfofs:",
                "    enabled: true",
                "    path: /serverinfo",
                "    config:",
                '      version: "1.0.0"',
                "  localfs:",
                "    enabled: true",
                "    path: /local",
                "    config:",
                f'      local_dir: "{data_dir}"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def build_runtime_tree(repo_root: Path, run: Path) -> Path:
    runtime = run / "rtc-runtime"
    if runtime.exists():
        shutil.rmtree(runtime)
    run_resolved = run.resolve()

    def ignore(dir_name: str, names: list[str]) -> set[str]:
        ignored = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
        current = Path(dir_name).resolve()
        ignored.update({".cache", "output_logs", "include", "repo"})
        if current == repo_root.resolve():
            ignored.update({".git", ".venv", runtime.name})
        if current == run_resolved:
            ignored.update(names)
        if current == (repo_root / "scripts" / "SWE" / "claude").resolve():
            ignored.update({".cache", "output_logs", "repo"})
        return ignored.intersection(names)

    shutil.copytree(repo_root, runtime, ignore=ignore)
    overlay = repo_root / "code-version"
    if overlay.is_dir():
        shutil.copytree(overlay, runtime, dirs_exist_ok=True)
    return runtime


def command_start(args: argparse.Namespace) -> int:
    root = repo_root_from_plugin()
    run = runtime_dir(args)
    logs = run / "logs"
    data_dir = run / "agfs-data"
    logs.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    rtc_pid_file = run / "retrieval-token-cutter.pid"
    agfs_pid_file = run / "agfs.pid"
    rtc_pid = read_pid(rtc_pid_file)
    agfs_pid = read_pid(agfs_pid_file)
    if rtc_pid and agfs_pid and pid_alive(rtc_pid) and pid_alive(agfs_pid):
        print(f"Already running: {api_url()}")
        print(f"Runtime dir: {run}")
        return 0

    agfs_port = int(os.environ.get("AGFS_HTTP_PORT") or "1833")
    rtc_url = api_url()
    agfs_url = (os.environ.get("AGFS_BASE_URL") or f"http://127.0.0.1:{agfs_port}").rstrip("/")
    env = os.environ.copy()
    env.setdefault("RTC_URL", rtc_url)
    env.setdefault("AGFS_BASE_URL", agfs_url)
    env.setdefault("VECTOR_DB_TYPE", "memory")
    env.setdefault("RTC_CODE_TOGGLE", "true")
    env.setdefault("EMBEDDING_PROVIDER", "openai")
    env.setdefault("RTC_EMBEDDING_MODEL", "text-embedding-3-small")
    env.setdefault("RTC_EMBEDDING_BASE_URL", "https://api.openai-proxy.org")
    env.setdefault("RTC_START_LOCAL_EMBED_SERVER", "0")

    agfs_config = run / "agfs-config.yaml"
    write_agfs_config(agfs_config, data_dir, agfs_port)
    runtime_root = build_runtime_tree(root, run)
    env["PYTHONPATH"] = f"{runtime_root}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)

    agfs_bin = find_agfs_bin(root)
    with (logs / "agfs-server.log").open("ab") as agfs_log:
        agfs_proc = subprocess.Popen(
            [agfs_bin, "-c", str(agfs_config)],
            stdout=agfs_log,
            stderr=subprocess.STDOUT,
            cwd=str(root),
            env=env,
            start_new_session=True,
        )
    agfs_pid_file.write_text(str(agfs_proc.pid), encoding="utf-8")

    py_bin = os.environ.get("PY_BIN") or sys.executable
    with (logs / "retrieval-token-cutter-server.log").open("ab") as server_log:
        server_proc = subprocess.Popen(
            [py_bin, str(runtime_root / "server" / "app.py")],
            stdout=server_log,
            stderr=subprocess.STDOUT,
            cwd=str(runtime_root),
            env=env,
            start_new_session=True,
        )
    rtc_pid_file.write_text(str(server_proc.pid), encoding="utf-8")

    for _ in range(max(1, int(args.wait))):
        try:
            get_json("/api/v1/health", timeout=2)
            print(f"Started Retrieval Token Cutter: {rtc_url}")
            print(f"Runtime dir: {run}")
            print(f"Logs: {logs}")
            return 0
        except Exception:
            time.sleep(1)

    print(f"Started processes, but health check did not pass yet: {rtc_url}", file=sys.stderr)
    print(f"Check logs: {logs}", file=sys.stderr)
    return 1


def command_stop(args: argparse.Namespace) -> int:
    run = runtime_dir(args)
    stopped = 0
    for name in ("retrieval-token-cutter", "agfs"):
        pid_file = run / f"{name}.pid"
        pid = read_pid(pid_file)
        if not pid:
            continue
        if pid_alive(pid):
            try:
                os.kill(pid, signal.SIGTERM)
                stopped += 1
            except ProcessLookupError:
                pass
        try:
            pid_file.unlink()
        except FileNotFoundError:
            pass
    print(f"Stopped {stopped} process(es). Runtime dir: {run}")
    return 0


def command_status(args: argparse.Namespace) -> int:
    run = runtime_dir(args)
    status = {}
    for name in ("retrieval-token-cutter", "agfs"):
        pid = read_pid(run / f"{name}.pid")
        status[name] = {"pid": pid, "alive": bool(pid and pid_alive(pid))}
    try:
        status["health"] = get_json("/api/v1/health", timeout=3)
    except Exception as exc:
        status["health_error"] = str(exc)
    print(json.dumps(status, indent=2, ensure_ascii=False))
    return 0 if status.get("retrieval-token-cutter", {}).get("alive") else 1


def command_health(_: argparse.Namespace) -> int:
    try:
        print(json.dumps(get_json("/api/v1/health"), indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(f"health failed: {exc}", file=sys.stderr)
        return 1


def command_compose(args: argparse.Namespace) -> int:
    query = " ".join(args.query).strip()
    if not query:
        print("usage: rtc-compose <query>", file=sys.stderr)
        return 2
    body = {**identity(args.session_id), "prompt": query}
    try:
        data = post_json("/api/v1/compose", body, timeout=args.timeout)
    except Exception as exc:
        print(f"compose failed: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(format_compose(data))
    return 0


def command_after_turn(args: argparse.Namespace) -> int:
    if args.transcript:
        path = Path(args.transcript)
        if not path.is_file():
            print(f"transcript not found: {path}", file=sys.stderr)
            return 1
        messages = parse_transcript_chunk(path.read_text(encoding="utf-8", errors="replace"))
        session_id = args.session_id or path.stem
    else:
        raw = sys.stdin.read()
        messages = parse_transcript_chunk(raw)
        session_id = args.session_id or "terminal-session"
    if not messages:
        print("No valid transcript messages found.")
        return 0
    body = {**identity(session_id), "messages": messages, "hook_event_name": "terminal"}
    try:
        data = post_json("/api/v1/after_turn", body, timeout=args.timeout)
    except Exception as exc:
        print(f"after-turn failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


def command_add_history(args: argparse.Namespace) -> int:
    base = project_transcript_dir(args.project_dir)
    if not base.is_dir():
        print(f"No Claude transcript directory found: {base}")
        return 0
    transcripts = sorted(
        p for p in base.rglob("*.jsonl")
        if "subagents" not in p.parts and not p.name.endswith(".ingest-offset")
    )
    pending = []
    skipped = 0
    total_size = 0
    for path in transcripts:
        off = Path(str(path) + ".ingest-offset")
        if off.is_file():
            try:
                if int(off.read_text().strip()) >= path.stat().st_size:
                    skipped += 1
                    continue
            except ValueError:
                pass
        pending.append(path)
        total_size += path.stat().st_size
    print(f"Project transcript dir: {base}")
    print(f"Pending transcripts: {len(pending)}")
    print(f"Skipped already ingested: {skipped}")
    print(f"Total pending size: {total_size / 1024 / 1024:.1f} MB")
    if args.dry_run:
        return 0
    if not args.yes:
        print("Refusing to import without --yes. Run with --dry-run first if unsure.")
        return 2
    ok = fail = empty = 0
    for path in pending:
        messages = parse_transcript_chunk(path.read_text(encoding="utf-8", errors="replace"))
        if not messages:
            empty += 1
            continue
        body = {**identity(path.stem), "messages": messages, "hook_event_name": "terminal-add-history"}
        try:
            post_json("/api/v1/after_turn", body, timeout=args.timeout)
            Path(str(path) + ".ingest-offset").write_text(str(path.stat().st_size))
            ok += 1
            print(f"OK {path.name}: {len(messages)} messages")
        except Exception as exc:
            fail += 1
            print(f"FAIL {path.name}: {exc}", file=sys.stderr)
    print(f"Done: ok={ok} fail={fail} empty={empty} skipped={skipped}")
    return 1 if fail else 0


def hook_compose() -> int:
    raw = sys.stdin.read()
    try:
        hook = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        log("call_compose", "invalid hook JSON")
        return 0
    prompt = str(hook.get("prompt") or "").strip()
    session_id = str(hook.get("session_id") or "unknown")
    if len(prompt) < 4 or prompt.startswith("/"):
        return 0
    additions: list[str] = []
    if looks_like_code_prompt(prompt):
        policy = code_policy_prompt()
        if policy:
            additions.append(policy)
    try:
        data = post_json("/api/v1/compose", {**identity(session_id), "prompt": prompt}, timeout=30)
        log("call_compose", f"POST {api_url()}/api/v1/compose session={session_id} prompt_len={len(prompt)}")
    except Exception as exc:
        log("call_compose", f"failed: {exc}")
        data = {}
    if data:
        additional = format_compose(data)
        if additional == "No relevant context found.":
            log("call_compose", "No relevant context returned")
        else:
            additions.append(f"[Retrieval Token Cutter]\n{additional[:9500]}")
    if not additions:
        return 0
    out = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": "\n\n".join(additions),
        }
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    return 0


def hook_add_session_message() -> int:
    raw = sys.stdin.read()
    try:
        hook = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        log("call_add_session_message", "invalid hook JSON")
        return 0
    session_id = str(hook.get("session_id") or "unknown")
    tool = str(hook.get("tool_name") or "unknown_tool")
    if session_id == "unknown" or tool not in SIDE_EFFECT_TOOLS:
        return 0
    content = "\n".join([
        f"[PostToolUse] {tool}",
        f"tool_input: {compact_json(hook.get('tool_input'))}",
        f"tool_response: {compact_json(hook.get('tool_response'))}",
    ])
    body = {**identity(session_id), "role": "tool", "content": content}
    try:
        data = post_json(f"/api/v1/sessions/{session_id}/messages", body, timeout=8)
        log("call_add_session_message", f"tool={tool} POST session message ok={data.get('ok', True)}")
    except Exception as exc:
        log("call_add_session_message", f"failed: {exc}")
    return 0


def hook_after_turn() -> int:
    raw = sys.stdin.read()
    try:
        hook = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        log("call_after_turn", "invalid hook JSON")
        return 0
    session_id = str(hook.get("session_id") or "unknown")
    transcript = str(hook.get("transcript_path") or "")
    event = str(hook.get("hook_event_name") or "unknown")
    if session_id == "unknown" or not transcript or not os.path.isfile(transcript):
        return 0
    path = Path(transcript)
    offset_path = Path(transcript + ".ingest-offset")
    try:
        offset = int(offset_path.read_text().strip()) if offset_path.is_file() else 0
    except ValueError:
        offset = 0
    size = path.stat().st_size
    if size <= offset:
        return 0
    with path.open("r", encoding="utf-8", errors="replace") as f:
        f.seek(offset)
        chunk = f.read()
    messages = parse_transcript_chunk(chunk)
    if not messages:
        offset_path.write_text(str(size))
        return 0
    body = {**identity(session_id), "messages": messages, "hook_event_name": event}
    try:
        post_json("/api/v1/after_turn", body, timeout=10)
        offset_path.write_text(str(size))
        log("call_after_turn", f"POST after_turn session={session_id} msgs={len(messages)}")
    except Exception as exc:
        log("call_after_turn", f"failed: {exc}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rtc", description="Retrieval Token Cutter terminal plugin commands")
    sub = parser.add_subparsers(dest="command", required=True)

    health = sub.add_parser("health", help="Check Retrieval Token Cutter health")
    health.set_defaults(func=command_health)

    start = sub.add_parser("start", help="Start local AGFS and Retrieval Token Cutter services")
    start.add_argument("--runtime-dir")
    start.add_argument("--wait", type=int, default=30)
    start.set_defaults(func=command_start)

    stop = sub.add_parser("stop", help="Stop services started by rtc start")
    stop.add_argument("--runtime-dir")
    stop.set_defaults(func=command_stop)

    status = sub.add_parser("status", help="Show service status")
    status.add_argument("--runtime-dir")
    status.set_defaults(func=command_status)

    compose = sub.add_parser("compose", help="Compose memory context for a query")
    compose.add_argument("query", nargs="*")
    compose.add_argument("--session-id")
    compose.add_argument("--json", action="store_true")
    compose.add_argument("--timeout", type=float, default=30)
    compose.set_defaults(func=command_compose)

    after = sub.add_parser("after-turn", help="Ingest one transcript or stdin JSONL")
    after.add_argument("--transcript")
    after.add_argument("--session-id")
    after.add_argument("--timeout", type=float, default=60)
    after.set_defaults(func=command_after_turn)

    hist = sub.add_parser("add-history", help="Import current project's Claude transcript history")
    hist.add_argument("--project-dir")
    hist.add_argument("--dry-run", action="store_true")
    hist.add_argument("--yes", action="store_true")
    hist.add_argument("--timeout", type=float, default=60)
    hist.set_defaults(func=command_add_history)

    hook = sub.add_parser("_hook", help=argparse.SUPPRESS)
    hook.add_argument("name", choices=["compose", "add-session-message", "after-turn"])
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "_hook":
        if args.name == "compose":
            return hook_compose()
        if args.name == "add-session-message":
            return hook_add_session_message()
        if args.name == "after-turn":
            return hook_after_turn()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
