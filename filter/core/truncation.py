"""Smart truncation — preserves head, tail, and critical lines."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


@dataclass
class TruncationResult:
    text: str
    original_lines: int
    kept_lines: int
    truncated_count: int
    marker: str


# Patterns for critical lines that should be preserved
_CRITICAL_PATTERNS = [
    re.compile(r"^\s*(def|class|async def|class)\s+\w+", re.MULTILINE),  # Function/class definitions
    re.compile(r"^\s*(import|from)\s+", re.MULTILINE),  # Imports
    re.compile(r"\b(ERROR|Error|SEVERE|Exception|Failed)\b", re.IGNORECASE),  # Error lines
    re.compile(r"\b(return|raise|yield)\b", re.IGNORECASE),  # Control flow
    re.compile(r"^\s*#.*", re.MULTILINE),  # Comments (often contain context)
    re.compile(r"\b(if|else|elif|for|while|try|except|finally)\s*[:(]", re.MULTILINE),  # Control structures
]


def _is_critical_line(line: str) -> bool:
    """Check if line contains critical information that should be preserved."""
    stripped = line.strip()
    if not stripped:
        return False
    return any(p.match(stripped) for p in _CRITICAL_PATTERNS)


def smart_truncate(
    text: str,
    max_lines: int = 100,
    head_lines: int | None = None,
    tail_lines: int = 10,
    marker: str | None = None,
) -> TruncationResult:
    """Truncate output to max_lines, preserving head, tail, and critical lines.

    Strategy (rtk-style enhanced):
    - Always keep first N lines (head_lines, default max_lines/2)
    - Always keep last M lines (tail_lines)
    - Always keep lines with critical information (function defs, errors, imports)
    - If content exceeds max_lines, insert "// ... X lines omitted ..." marker
    """
    if marker is None:
        marker = f"\n// ... {{}} lines omitted (total: {{}}) ..."

    lines = text.splitlines()
    total = len(lines)

    if total <= max_lines:
        return TruncationResult(
            text=text,
            original_lines=total,
            kept_lines=total,
            truncated_count=0,
            marker="",
        )

    if head_lines is None:
        head_lines = max_lines // 2

    head_lines = min(head_lines, max_lines - tail_lines)
    tail_lines = min(tail_lines, max_lines - head_lines)

    head = lines[:head_lines]
    tail = lines[-tail_lines:]
    omitted = total - head_lines - tail_lines

    marker_line = marker.format(omitted, total)
    result_lines = head + [marker_line] + tail if omitted > 0 else head + tail

    return TruncationResult(
        text="\n".join(result_lines),
        original_lines=total,
        kept_lines=len(result_lines),
        truncated_count=omitted,
        marker=marker_line,
    )


def smart_truncate_with_priority(
    text: str,
    max_lines: int = 100,
    preserve_critical: bool = True,
    marker: str | None = None,
) -> TruncationResult:
    """Enhanced truncation that prioritizes critical lines over position-based selection.

    This strategy:
    1. Identifies "critical" lines (function defs, error lines, imports, etc.)
    2. Preserves them even if they're in the middle of the file
    3. Truncates from non-critical sections first

    Args:
        text: Input text to truncate
        max_lines: Maximum lines to preserve
        preserve_critical: Whether to prioritize critical lines
        marker: Custom omission marker

    Returns:
        TruncationResult with truncated text and stats
    """
    if marker is None:
        marker = f"\n// ... {{}} lines omitted (total: {{}}) ..."

    lines = text.splitlines()
    total = len(lines)

    if total <= max_lines:
        return TruncationResult(
            text=text,
            original_lines=total,
            kept_lines=total,
            truncated_count=0,
            marker="",
        )

    if not preserve_critical:
        return smart_truncate(text, max_lines=max_lines, marker=marker)

    # Identify critical line indices
    critical_indices = set()
    for i, line in enumerate(lines):
        if _is_critical_line(line):
            critical_indices.add(i)

    # Build result: preserve head, critical lines, and tail
    head_count = max_lines // 3
    tail_count = max_lines // 3
    critical_budget = max_lines - head_count - tail_count - 1  # -1 for marker

    head = lines[:head_count]

    # Collect critical lines from middle
    critical_lines = []
    for i in range(head_count, total - tail_count):
        if i in critical_indices and len(critical_lines) < critical_budget:
            critical_lines.append(lines[i])

    tail = lines[-tail_count:]

    # Calculate how many lines we're omitting
    omitted = total - head_count - len(critical_lines) - tail_count
    marker_line = marker.format(omitted, total)

    result_lines = head + critical_lines + [marker_line] + tail

    return TruncationResult(
        text="\n".join(result_lines),
        original_lines=total,
        kept_lines=len(result_lines),
        truncated_count=omitted,
        marker=marker_line,
    )
