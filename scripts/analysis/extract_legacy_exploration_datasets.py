#!/usr/bin/env python3
"""Split legacy Claude traces by first code-exploration tool.

Outputs four datasets:
- grep.jsonl: native Grep, or shell grep/rg as the first command
- glob.jsonl: native Glob
- find.jsonl: shell find as the first command
- direct_read.jsonl: direct Read of a code-ish file
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from extract_legacy_search_dataset import (  # noqa: E402
    compact_content,
    issue_metadata,
    load_jsonl,
    normalize_target,
    parse_shell_search,
    relpath,
    result_for_event,
    tool_uses,
)


CODE_EXTENSIONS = {
    ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs",
    ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".scala",
    ".kt", ".kts", ".swift", ".m", ".mm", ".sh", ".bash", ".zsh",
    ".toml", ".yaml", ".yml", ".json", ".ini", ".cfg", ".txt", ".rst",
    ".md",
}
SKIP_READ_NAMES = {"TASK.md", "RUN_IN_SWE_LOCAL_ENV.sh"}


def first_command(command: str) -> str:
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
    return next((part for part in parts if part not in {"env"} and not part.startswith("-")), "")


def parse_shell_find(command: str) -> dict[str, Any] | None:
    if first_command(command) != "find":
        return None
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
    root = parts[1] if len(parts) > 1 and not parts[1].startswith("-") else ""
    return {
        "method": "find",
        "tool": "shell_find",
        "query": command,
        "path": root,
        "command": command,
        "input": {"command": command},
    }


def read_is_codeish(path: str) -> bool:
    if not path:
        return False
    name = Path(path).name
    if name in SKIP_READ_NAMES:
        return False
    return Path(path).suffix.lower() in CODE_EXTENSIONS


def normalize_starter(tool: dict[str, Any]) -> dict[str, Any] | None:
    name = tool.get("name")
    data = tool.get("input") or {}

    if name == "Grep":
        query = str(data.get("pattern") or "").strip()
        if not query:
            return None
        return {
            "method": "grep",
            "tool": "Grep",
            "query": query,
            "path": str(data.get("path") or ""),
            "command": "",
            "input": data,
        }

    if name == "Glob":
        pattern = str(data.get("pattern") or data.get("glob") or "").strip()
        if not pattern:
            return None
        return {
            "method": "glob",
            "tool": "Glob",
            "query": pattern,
            "path": str(data.get("path") or ""),
            "command": "",
            "input": data,
        }

    if name == "Read":
        path = str(data.get("file_path") or "")
        if not read_is_codeish(path):
            return None
        return {
            "method": "direct_read",
            "tool": "Read",
            "query": path,
            "path": path,
            "command": "",
            "input": data,
        }

    if name == "Bash":
        command = str(data.get("command") or "")
        grep = parse_shell_search(command)
        if grep:
            return {
                "method": "grep",
                "tool": grep.get("kind"),
                "query": grep.get("query"),
                "path": grep.get("path"),
                "command": command,
                "input": data,
            }
        find = parse_shell_find(command)
        if find:
            return find
    return None


def make_target_from_read_starter(tool: dict[str, Any], event: dict[str, Any], result: dict[str, Any], workspace: str) -> dict[str, Any]:
    data = tool.get("input") or {}
    path = str(data.get("file_path") or "")
    return {
        "kind": "Read",
        "path": relpath(path, workspace),
        "offset": data.get("offset"),
        "limit": data.get("limit"),
        "timestamp": event.get("timestamp"),
        "tool_input": data,
        "result": result,
        "is_start_target": True,
    }


def extract_run(run_dir: Path, max_targets: int) -> dict[str, list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    for log_path in sorted((run_dir / "logs").glob("*.jsonl")):
        events.extend(load_jsonl(log_path))

    events_by_parent: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        parent = event.get("parentUuid")
        if parent:
            events_by_parent.setdefault(str(parent), []).append(event)

    records_by_method: dict[str, list[dict[str, Any]]] = {
        "grep": [],
        "glob": [],
        "find": [],
        "direct_read": [],
    }
    meta = issue_metadata(run_dir)
    active: dict[str, Any] | None = None
    target_count = 0

    for event_index, event in enumerate(events):
        for use in tool_uses(event):
            starter = normalize_starter(use)
            if starter:
                tool_id = str(use.get("id") or "")
                result = result_for_event(events_by_parent, event, tool_id)
                workspace = str(event.get("cwd") or run_dir / "workspace")
                start_path = relpath(str(starter.get("path") or ""), workspace)
                record = {
                    "dataset_version": 1,
                    "run_dir": str(run_dir),
                    "log_path": event.get("_log_path"),
                    "event_index": event_index,
                    "timestamp": event.get("timestamp"),
                    "workspace": workspace,
                    **meta,
                    "start": {
                        "method": starter.get("method"),
                        "tool": starter.get("tool"),
                        "query": starter.get("query"),
                        "path": start_path,
                        "command": starter.get("command"),
                        "input": starter.get("input"),
                    },
                    "start_result": result,
                    "targets": [],
                }
                if starter.get("method") == "direct_read":
                    record["targets"].append(make_target_from_read_starter(use, event, result, workspace))
                    records_by_method["direct_read"].append(record)
                    # A direct Read is also a target for the current grep/glob/find starter.
                    if active and target_count < max_targets:
                        active["targets"].append(make_target_from_read_starter(use, event, result, workspace))
                        target_count += 1
                    continue

                if active:
                    records_by_method[active["start"]["method"]].append(active)
                active = record
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
        records_by_method[active["start"]["method"]].append(active)
    return records_by_method


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-root", default="scripts/SWE/claude/legacy/output_logs")
    parser.add_argument("--out-dir", default="artifacts/legacy-exploration-datasets")
    parser.add_argument("--max-targets", type=int, default=4)
    args = parser.parse_args()

    root = Path(args.legacy_root)
    out_dir = Path(args.out_dir)
    run_dirs = sorted(path for path in root.iterdir() if (path / "logs").is_dir())
    all_by_method: dict[str, list[dict[str, Any]]] = {
        "grep": [],
        "glob": [],
        "find": [],
        "direct_read": [],
    }

    for run_dir in run_dirs:
        by_method = extract_run(run_dir, args.max_targets)
        for method, rows in by_method.items():
            all_by_method[method].extend(rows)

    summary = {"runs": len(run_dirs), "datasets": {}}
    for method, rows in all_by_method.items():
        path = out_dir / f"{method}.jsonl"
        write_jsonl(path, rows)
        summary["datasets"][method] = {
            "records": len(rows),
            "records_with_targets": sum(1 for row in rows if row.get("targets")),
            "output": str(path),
        }

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
