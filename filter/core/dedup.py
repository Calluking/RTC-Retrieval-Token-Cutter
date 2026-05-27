"""Line-level deduplication with error/warning grouping."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Literal


@dataclass
class DedupResult:
    """Result of a deduplication operation."""
    text: str
    original_lines: int
    deduplicated_lines: int
    collapsed_repeats: int
    grouping_type: Literal["none", "error", "warning"] = "none"


# Error/Warning grouping patterns
_ERROR_PATTERNS = [
    re.compile(r"\b(ERROR|Error|error|SEVERE|Severe)\b.*", re.IGNORECASE),
    re.compile(r"\bFAIL(ED|URE)?\b.*", re.IGNORECASE),
    re.compile(r"^\s*Traceback\s*\(most recent call last\)", re.MULTILINE),
    re.compile(r"^\s*File\s+\".*\",\s+line\s+\d+", re.MULTILINE),
    re.compile(r"\bException\b.*", re.IGNORECASE),
    re.compile(r"\bFailed to\b.*", re.IGNORECASE),
    re.compile(r"\berrno\s*[=:]\s*\d+", re.IGNORECASE),
]

_WARNING_PATTERNS = [
    re.compile(r"\b(WARN(ING)?|Warning|warning)\b.*", re.IGNORECASE),
    re.compile(r"\bDeprecat(ed|ion)\b.*", re.IGNORECASE),
    re.compile(r"\bdeprecated\b.*", re.IGNORECASE),
    re.compile(r"\bCaution\b.*", re.IGNORECASE),
    re.compile(r"\bUnsupported\b.*", re.IGNORECASE),
]


def _is_error_line(line: str) -> bool:
    """Check if line matches error patterns."""
    return any(p.match(line.strip()) for p in _ERROR_PATTERNS)


def _is_warning_line(line: str) -> bool:
    """Check if line matches warning patterns."""
    return any(p.match(line.strip()) for p in _WARNING_PATTERNS)


def deduplicate(text: str, max_adjacent: int = 3) -> str:
    """Collapse consecutive identical lines into one + count indicator.

    Example:
        DEBUG: foo
        DEBUG: foo
        DEBUG: foo
    becomes:
        DEBUG: foo
        // ... line repeated 2 times (total: 3)

    Also collapses runs of whitespace-only lines.
    """
    lines = text.splitlines()
    if not lines:
        return text

    result: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Collapse multiple blank lines to one
        if stripped == "":
            if result and result[-1].strip() != "":
                result.append("")
            i += 1
            continue

        # Count repetitions
        j = i + 1
        while j < len(lines) and lines[j].strip() == stripped:
            j += 1
        count = j - i

        if count > max_adjacent:
            result.append(stripped)
            result.append(f"// ... line repeated {count - 1} times (total: {count})")
        else:
            for _ in range(count):
                result.append(stripped if stripped == line else line)

        i = j

    return "\n".join(result)


def deduplicate_with_grouping(text: str, group_errors: bool = True, group_warnings: bool = True, max_adjacent: int = 3) -> DedupResult:
    """Deduplicate text with error/warning grouping.

    Groups similar error and warning lines together, preserving unique
    information like stack trace line numbers while collapsing repeated
    error messages.

    Args:
        text: Input text to deduplicate
        group_errors: Whether to group similar error lines
        group_warnings: Whether to group similar warning lines

    Returns:
        DedupResult with deduplicated text and stats
    """
    lines = text.splitlines()
    if not lines:
        return DedupResult(
            text=text,
            original_lines=0,
            deduplicated_lines=0,
            collapsed_repeats=0,
            grouping_type="none",
        )

    original_count = len(lines)
    result: list[str] = []
    collapsed = 0

    # Track error/warning groups
    error_groups: dict[str, list[int]] = {}
    warning_groups: dict[str, list[int]] = {}

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip empty lines
        if stripped == "":
            result.append(line)  # Preserve original whitespace
            continue

        # Check for error line
        if group_errors and _is_error_line(line):
            # Extract base pattern (normalize line numbers in stack traces)
            base = _normalize_error_pattern(stripped)
            if base in error_groups:
                error_groups[base].append(i)
                collapsed += 1
                continue
            else:
                error_groups[base] = [i]

        # Check for warning line
        if group_warnings and _is_warning_line(line):
            base = _normalize_warning_pattern(stripped)
            if base in warning_groups:
                warning_groups[base].append(i)
                collapsed += 1
                continue
            else:
                warning_groups[base] = [i]

        # Count consecutive duplicates
        j = i + 1
        while j < len(lines) and lines[j].strip() == stripped:
            j += 1
        count = j - i

        if count > max_adjacent:
            result.append(stripped)
            result.append(f"// ... line repeated {count - 1} times (total: {count})")
            collapsed += count - 1
        else:
            for k in range(i, j):
                result.append(lines[k])

    grouping_type: Literal["none", "error", "warning"] = "none"
    if error_groups:
        grouping_type = "error"
    elif warning_groups:
        grouping_type = "warning"

    return DedupResult(
        text="\n".join(result),
        original_lines=original_count,
        deduplicated_lines=len(result),
        collapsed_repeats=collapsed,
        grouping_type=grouping_type,
    )


def _normalize_error_pattern(line: str) -> str:
    """Normalize error line for grouping - replace variable parts."""
    # Replace line numbers in "File X, line Y" patterns
    normalized = re.sub(r'File\s+".*?",\s+line\s+\d+', 'File "...", line <N>', line)
    # Replace hex addresses in traceback
    normalized = re.sub(r'0x[0-9a-fA-F]+', '<ADDR>', normalized)
    # Replace errno numbers
    normalized = re.sub(r'\berrno\s*[=:]\s*\d+', 'errno=<N>', normalized)
    return normalized


def _normalize_warning_pattern(line: str) -> str:
    """Normalize warning line for grouping."""
    # Replace version numbers
    normalized = re.sub(r'\d+\.\d+', '<VER>', line)
    # Replace paths
    normalized = re.sub(r'/[^\s]+', '<PATH>', normalized)
    return normalized
