"""Git output handlers — compact git status, log, diff."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class GitParseResult:
    summary: str
    detail: str
    original_lines: int
    saved_tokens_estimate: int


def compact_git_status(raw: str) -> GitParseResult:
    """Parse `git status --porcelain` into grouped summary + detail."""
    original_lines = raw.count("\n") + (1 if raw and not raw.endswith("\n") else 0)

    staged: list[str] = []
    modified: list[str] = []
    untracked: list[str] = []
    clean = False

    for line in raw.splitlines():
        if not line.strip():
            continue
        if len(line) < 2:
            continue
        index_st, worktree_st = line[0], line[1]
        filename = line[3:] if len(line) > 3 else ""

        if index_st == "?" and worktree_st == "?":
            untracked.append(filename)
        elif index_st == " " and worktree_st == "M":
            modified.append(filename)
        elif index_st == "M" and worktree_st == " ":
            staged.append(filename)
        elif index_st == "M" and worktree_st == "M":
            staged.append(f"{filename} (both modified)")
        elif index_st == "A":
            staged.append(f"{filename} (added)")
        elif index_st == "D":
            staged.append(f"{filename} (deleted)")
        elif index_st == "R":
            staged.append(f"{filename} (renamed)")
        elif index_st == "!":
            pass  # ignored
        else:
            if index_st not in (" ", "?"):
                staged.append(f"{filename} [{index_st}{worktree_st}]")
            elif worktree_st not in (" ", "?"):
                modified.append(f"{filename} [{index_st}{worktree_st}]")

    if not staged and not modified and not untracked:
        clean = True

    # Build summary
    parts: list[str] = []
    if staged:
        parts.append(f"+ Staged: {len(staged)} file(s)")
        for s in staged:
            parts.append(f"  {s}")
    if modified:
        parts.append(f"~ Modified: {len(modified)} file(s)")
        for m in modified:
            parts.append(f"  {m}")
    if untracked:
        parts.append(f"? Untracked: {len(untracked)} file(s)")
        for u in untracked:
            parts.append(f"  {u}")
    if clean:
        parts.append("// (working tree clean)")

    summary_parts = [p for p in parts if not p.startswith("  ")]
    detail_parts = [p for p in parts if p.startswith("  ")]

    summary = "\n".join(summary_parts) if summary_parts else "// no changes"
    detail = "\n".join(detail_parts) if detail_parts else ""

    # Rough token estimate: original chars vs summary+detail chars
    saved = max(0, len(raw) - len(summary) - len(detail))

    return GitParseResult(
        summary=summary,
        detail=detail,
        original_lines=original_lines,
        saved_tokens_estimate=saved // 4,
    )


def compact_git_log(raw: str, limit: int = 10) -> str:
    """Compact git log into one line per commit."""
    lines = raw.splitlines()
    if not lines:
        return raw

    result: list[str] = []
    current_commit: list[str] = []

    def flush_commit(commit_lines: list[str]) -> None:
        if not commit_lines:
            return
        # First line: hash + subject
        first = commit_lines[0]
        m = re.match(r"([a-f0-9]+)\s+(.*)", first)
        if m:
            hash_part = m.group(1)[:7]
            subject = m.group(2)
            result.append(f"{hash_part} {subject}")
        else:
            result.append(first[:80])

        # If commit has body (like BREAKING CHANGE notes), emit a hint
        body_lines = commit_lines[1:]
        if body_lines:
            body_text = " | ".join(b.strip() for b in body_lines if b.strip())
            if len(body_text) > 60:
                body_text = body_text[:60] + "..."
            result.append(f"  {body_text}")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Detect commit line (starts with hash)
        if re.match(r"^[a-f0-9]{7,}\s+", stripped) or re.match(r"^commit\s+[a-f0-9]", stripped, re.IGNORECASE):
            flush_commit(current_commit)
            current_commit = [stripped]
        else:
            current_commit.append(stripped)

    flush_commit(current_commit)

    total = len(result)
    if total > limit:
        result = result[:limit] + [f"// ... {total - limit} more commits"]

    return "\n".join(result)


def compact_git_diff(raw: str) -> str:
    """For git diff: show stat line per file, then truncated unified diff."""
    lines = raw.splitlines()
    if not lines:
        return raw

    stat_lines: list[str] = []
    diff_lines: list[str] = []
    in_diff = False

    for line in lines:
        if line.startswith("diff --git") or line.startswith("@@"):
            in_diff = True
        if not in_diff:
            stat_lines.append(line)
        else:
            diff_lines.append(line)

    # Build stat summary
    stat_summary: list[str] = []
    file_stats: dict[str, tuple[int, int]] = {}
    for line in stat_lines:
        # mode/filename lines
        m = re.match(r"^(?:old mode|new mode|deleted file mode|new file mode|index|link)", line)
        if m:
            continue
        # file + ... | N ++++-
        m2 = re.match(r"^(.+?)\s*\|\s*(\d+)\s*([+\-]+)", line)
        if m2:
            filename = m2.group(1).strip()
            changes = len(m2.group(3))
            stat_summary.append(f"{filename}: {m2.group(2)} lines, {changes} changes")
        else:
            if line.strip():
                stat_summary.append(line)

    diff_truncated = "\n".join(diff_lines[:80])
    if len(diff_lines) > 80:
        diff_truncated += f"\n// ... {len(diff_lines) - 80} diff lines omitted"

    return "\n".join(stat_summary) + "\n--- Diff ---\n" + diff_truncated


def git_handler_factory(command: str) -> callable:
    """Return the appropriate git subcommand handler."""
    if command == "git-status" or command == "status":
        return compact_git_status
    elif command == "git-log" or command == "log":
        return compact_git_log
    elif command == "git-diff" or command == "diff":
        return compact_git_diff
    return lambda x: x


class GitHandler:
    """Dispatches git subcommand output to the right compact handler."""

    SUBCOMMANDS = {
        "status": compact_git_status,
        "log": compact_git_log,
        "diff": compact_git_diff,
    }

    def __call__(self, command: str, text: str) -> str:
        # Normalize: "git status" -> "status"
        sub = command.split()[-1] if " " in command else command
        handler = self.SUBCOMMANDS.get(sub)
        if handler:
            result = handler(text)
            # Handler may return GitParseResult (status) or str (log/diff)
            if hasattr(result, "summary"):
                parts = [result.summary]
                if result.detail:
                    parts.append(result.detail)
                return "\n".join(parts)
            return result
        return text