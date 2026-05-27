"""Summarizer — generic output summarization engine."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class SummaryResult:
    text: str
    original_size: int
    summary_size: int
    saved_tokens_estimate: int


def extract_errors(text: str, limit: int = 10) -> list[str]:
    """Extract error lines from output."""
    error_patterns = [
        r"(?i)error[:\s].*",
        r"(?i)exception[:\s].*",
        r"(?i)failed[:\s].*",
        r"Traceback \(most recent call last\)",
        r"(?i)panic[:\s].*",
    ]
    errors: list[str] = []
    for line in text.splitlines():
        for pat in error_patterns:
            if re.search(pat, line):
                errors.append(line.strip())
                break
    return errors[:limit]


def extract_warnings(text: str, limit: int = 10) -> list[str]:
    """Extract warning lines from output."""
    errors: list[str] = []
    for line in text.splitlines():
        lower = line.lower()
        if "warning" in lower or "warn:" in lower:
            errors.append(line.strip())
    return errors[:limit]


def summarize_generic(text: str, max_lines: int = 50) -> SummaryResult:
    """Generic summarizer: head + tail + errors + key metrics."""
    lines = text.splitlines()
    total = len(lines)

    if total <= max_lines:
        return SummaryResult(
            text=text,
            original_size=len(text),
            summary_size=len(text),
            saved_tokens_estimate=0,
        )

    head = lines[: max_lines // 2]
    tail = lines[-max_lines // 4 :] if total > max_lines else []
    errors = extract_errors(text)
    warnings = extract_warnings(text)

    parts: list[str] = []
    parts.extend(head)
    if errors:
        parts.append(f"// --- {len(errors)} error(s) ---")
        parts.extend(errors[:5])
    if warnings:
        parts.append(f"// --- {len(warnings)} warning(s) ---")
        parts.extend(warnings[:5])
    if tail and tail != head[-max_lines // 4:]:
        parts.append("// --- tail ---")
        parts.extend(tail)

    result = "\n".join(parts)
    saved = max(0, len(text) - len(result))
    return SummaryResult(
        text=result,
        original_size=len(text),
        summary_size=len(result),
        saved_tokens_estimate=saved // 4,
    )