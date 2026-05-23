#!/usr/bin/env python3
"""Extract legacy Claude code-search traces into retrieval training data.

The output is intentionally close to the agent's interaction trace:
each record is one search action and the target snippets/files the agent
looked at or edited before the next search.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
from pathlib import Path
from typing import Any


SEARCH_TOOLS = {"Grep"}
TARGET_TOOLS = {"Read", "Edit", "MultiEdit", "Write"}
SEARCH_SHELL_RE = re.compile(r"(^|[;&|]\s*)(grep|rg)\s+")
SHELL_SEARCH_EXCLUDE_RE = re.compile(
    r"RUN_IN_SWE_LOCAL_ENV|pytest|runtests\.py|pip install|python3? -c|conda |"
    r"git diff|git status|traceback|FAILED\\|PASSED|RequestsDependencyWarning"
)
GREP_OPTIONS_WITH_VALUE = {
    "-A",
    "-B",
    "-C",
    "-m",
    "--after-context",
    "--before-context",
    "--context",
    "--max-count",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            obj["_log_path"] = str(path)
            obj["_line_no"] = line_no
            rows.append(obj)
    return rows


def iter_content_blocks(event: dict[str, Any]) -> list[dict[str, Any]]:
    message = event.get("message") or {}
    content = message.get("content") or []
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        return [block for block in content if isinstance(block, dict)]
    return []


def tool_uses(event: dict[str, Any]) -> list[dict[str, Any]]:
    return [block for block in iter_content_blocks(event) if block.get("type") == "tool_use"]


def tool_result(event: dict[str, Any]) -> dict[str, Any] | None:
    message = event.get("message") or {}
    content = message.get("content")
    if not isinstance(content, list):
        return None
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_result":
            return block
    return None


def compact_content(value: Any, limit: int = 6000) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False)
    if len(text) > limit:
        return text[:limit] + f"\n... <truncated {len(text) - limit} chars>"
    return text


def parse_shell_search(command: str) -> dict[str, Any] | None:
    if not SEARCH_SHELL_RE.search(command):
        return None
    if SHELL_SEARCH_EXCLUDE_RE.search(command):
        return None
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
    first_command = next((part for part in parts if part not in {"env"} and not part.startswith("-")), "")
    if first_command not in {"grep", "rg"}:
        return None
    for idx, part in enumerate(parts):
        if part in {"grep", "rg"}:
            args = parts[idx + 1 :]
            query = ""
            path = ""
            skip_next = False
            invert_match = False
            for arg in args:
                if skip_next:
                    skip_next = False
                    continue
                if arg in GREP_OPTIONS_WITH_VALUE:
                    skip_next = True
                    continue
                if arg == "-v" or arg == "--invert-match":
                    invert_match = True
                    continue
                if arg.startswith("-"):
                    continue
                if not query:
                    query = arg
                elif not path:
                    path = arg
                    break
            if not query or query in {"|", "&&", ";"}:
                return None
            if invert_match and not query:
                continue
            return {"kind": f"shell_{part}", "query": query, "path": path, "command": command}
    return None


def normalize_search(tool: dict[str, Any]) -> dict[str, Any] | None:
    name = tool.get("name")
    data = tool.get("input") or {}
    if name in SEARCH_TOOLS:
        query = data.get("pattern") or data.get("path") or data.get("glob") or ""
        return {
            "kind": name,
            "query": str(query),
            "path": str(data.get("path") or ""),
            "tool_input": data,
            "command": "",
        }
    if name == "Bash":
        command = str(data.get("command") or "")
        return parse_shell_search(command)
    return None


def normalize_target(tool: dict[str, Any]) -> dict[str, Any] | None:
    name = tool.get("name")
    data = tool.get("input") or {}
    if name == "Read":
        return {
            "kind": "Read",
            "path": str(data.get("file_path") or ""),
            "offset": data.get("offset"),
            "limit": data.get("limit"),
            "tool_input": data,
        }
    if name in {"Edit", "MultiEdit", "Write"}:
        target = {
            "kind": str(name),
            "path": str(data.get("file_path") or ""),
            "tool_input": data,
        }
        if "old_string" in data:
            target["old_string"] = compact_content(data.get("old_string"), 3000)
        if "new_string" in data:
            target["new_string"] = compact_content(data.get("new_string"), 3000)
        if "edits" in data:
            target["edits"] = data.get("edits")
        return target
    return None


def result_for_event(events_by_parent: dict[str, list[dict[str, Any]]], tool_event: dict[str, Any], tool_id: str) -> dict[str, Any]:
    event_uuid = str(tool_event.get("uuid") or "")
    for child in events_by_parent.get(event_uuid, []):
        result = tool_result(child)
        if result and result.get("tool_use_id") == tool_id:
            return {
                "content": compact_content(result.get("content")),
                "structured": child.get("toolUseResult"),
            }
    return {"content": "", "structured": None}


def relpath(path: str, workspace: str) -> str:
    if not path or not workspace:
        return path
    try:
        return str(Path(path).resolve().relative_to(Path(workspace).resolve()))
    except Exception:
        return path


def issue_metadata(run_dir: Path) -> dict[str, Any]:
    instance_path = run_dir / "instance.json"
    if not instance_path.exists():
        return {}
    try:
        data = json.loads(instance_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {
        "instance_id": data.get("instance_id"),
        "repo": data.get("repo"),
        "base_commit": data.get("base_commit"),
        "problem_statement": compact_content(data.get("problem_statement"), 1200),
    }


def extract_run(run_dir: Path, max_targets: int) -> list[dict[str, Any]]:
    log_paths = sorted((run_dir / "logs").glob("*.jsonl"))
    events: list[dict[str, Any]] = []
    for log_path in log_paths:
        events.extend(load_jsonl(log_path))

    events_by_parent: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        parent = event.get("parentUuid")
        if parent:
            events_by_parent.setdefault(str(parent), []).append(event)

    meta = issue_metadata(run_dir)
    records: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    target_count = 0

    for event_index, event in enumerate(events):
        for use in tool_uses(event):
            search = normalize_search(use)
            if search:
                if active:
                    records.append(active)
                tool_id = str(use.get("id") or "")
                result = result_for_event(events_by_parent, event, tool_id)
                workspace = str(event.get("cwd") or run_dir / "workspace")
                active = {
                    "dataset_version": 1,
                    "run_dir": str(run_dir),
                    "log_path": event.get("_log_path"),
                    "event_index": event_index,
                    "timestamp": event.get("timestamp"),
                    "workspace": workspace,
                    **meta,
                    "search": {
                        "tool": search.get("kind"),
                        "query": search.get("query"),
                        "path": relpath(str(search.get("path") or ""), workspace),
                        "command": search.get("command"),
                        "input": search.get("tool_input"),
                    },
                    "search_result": result,
                    "targets": [],
                }
                target_count = 0
                continue

            if not active or target_count >= max_targets:
                continue
            target = normalize_target(use)
            if not target:
                continue
            tool_id = str(use.get("id") or "")
            result = result_for_event(events_by_parent, event, tool_id)
            workspace = str(active.get("workspace") or "")
            if target.get("path"):
                target["path"] = relpath(str(target.get("path")), workspace)
            target["timestamp"] = event.get("timestamp")
            target["result"] = result
            active["targets"].append(target)
            target_count += 1

    if active:
        records.append(active)
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-root", default="scripts/SWE/claude/legacy/output_logs")
    parser.add_argument("--out", default="artifacts/legacy-search-dataset/search_targets.jsonl")
    parser.add_argument("--summary-out", default="artifacts/legacy-search-dataset/summary.json")
    parser.add_argument("--max-targets", type=int, default=4)
    args = parser.parse_args()

    root = Path(args.legacy_root)
    run_dirs = sorted(path for path in root.iterdir() if (path / "logs").is_dir())
    all_records: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        all_records.extend(extract_run(run_dir, args.max_targets))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for record in all_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    summary = {
        "runs": len(run_dirs),
        "records": len(all_records),
        "records_with_targets": sum(1 for row in all_records if row.get("targets")),
        "by_tool": {},
        "output": str(out_path),
    }
    for record in all_records:
        tool = ((record.get("search") or {}).get("tool")) or "unknown"
        summary["by_tool"][tool] = summary["by_tool"].get(tool, 0) + 1

    summary_path = Path(args.summary_out)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
