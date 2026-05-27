"""Generic shell / arbitrary command output handler."""

from __future__ import annotations

import re
from dataclasses import dataclass

from filter.core.filter import MinimalFilter
from filter.core.truncation import smart_truncate
from filter.core.dedup import deduplicate


@dataclass
class OutputClassification:
    kind: str  # "test", "build", "log", "json", "list", "generic"
    confidence: float


def classify_output(text: str) -> OutputClassification:
    """Heuristically detect the output type."""
    first_lines = text.splitlines()[:10]
    joined = "\n".join(first_lines).lower()

    # Test results
    if any(k in joined for k in ["passed", "failed", "error", "test", "ok", "failures"]):
        return OutputClassification(kind="test", confidence=0.8)

    # Build output
    if any(k in joined for k in ["compiling", "building", "cargo", "cmake", "make", "error:", "warning"]):
        return OutputClassification(kind="build", confidence=0.7)

    # Log lines
    if any(k in joined for k in ["debug", "info", "warn", "error", "trace", "[0m", "http://"]):
        return OutputClassification(kind="log", confidence=0.7)

    # JSON
    if text.strip().startswith(("{" , "[")):
        return OutputClassification(kind="json", confidence=0.9)

    # Long single lines (file content)
    if len(text.splitlines()) < 5 and len(text) > 500:
        return OutputClassification(kind="generic", confidence=0.5)

    return OutputClassification(kind="generic", confidence=0.5)


def compact_test_output(text: str) -> str:
    """Extract pass/fail counts, errors, and truncate."""
    lines = text.splitlines()
    summary_lines: list[str] = []
    error_lines: list[str] = []
    passed = failed = 0

    for line in lines:
        lower = line.lower()
        if re.match(r"^\s*(passed|ok|pass)\s+\d+", lower) or "passed" in lower:
            passed += 1
            summary_lines.append(line.strip())
        elif re.match(r"^\s*(failed|fail|failure)\s+\d+", lower) or "failed" in lower:
            failed += 1
            summary_lines.append(line.strip())
        elif "error" in lower or "traceback" in lower:
            error_lines.append(line.strip())

    result = summary_lines[:20]
    if error_lines:
        result.append("// Errors:")
        result.extend(error_lines[:10])
    if passed or failed:
        result.append(f"// Summary: {passed} passed, {failed} failed")

    truncated = smart_truncate("\n".join(result), max_lines=50)
    return truncated.text


def compact_build_output(text: str) -> str:
    """Show first few lines + errors/warnings + last few lines."""
    lines = text.splitlines()
    head = lines[:15]
    errors = [l for l in lines if "error" in l.lower() or "warning:" in l.lower()]
    tail = lines[-10:] if len(lines) > 15 else []

    parts = head + (["// ... errors/warnings ..."] if errors else []) + errors[:5] + (["---"] if tail else []) + tail
    truncated = smart_truncate("\n".join(parts), max_lines=80)
    return truncated.text


def compact_json_output(text: str) -> str:
    """Show JSON structure: keys, array lengths, without full values."""
    lines = text.splitlines()
    summary: list[str] = []
    for line in lines[:30]:
        stripped = line.strip()
        if stripped.startswith('"'):
            key = stripped.split('"')[1] if '"' in stripped else stripped
            summary.append(f"  {key}: ...")
    if len(lines) > 30:
        summary.append(f"  // ... {len(lines) - 30} more lines ...")
    return "{\n" + "\n".join(summary) + "\n}"


def compact_log_output(text: str) -> str:
    """Dedupe + truncate log output."""
    deduped = deduplicate(text, max_adjacent=2)
    truncated = smart_truncate(deduped, max_lines=80)
    return truncated.text


class ShellHandler:
    """Route arbitrary shell output to the right compact handler."""

    def __call__(self, command: str, text: str) -> str:
        cls = classify_output(text)
        kind = cls.kind

        if kind == "test":
            return compact_test_output(text)
        elif kind == "build":
            return compact_build_output(text)
        elif kind == "json":
            return compact_json_output(text)
        elif kind == "log":
            return compact_log_output(text)
        else:
            # Generic: filter + dedupe + truncate
            filt = MinimalFilter()
            filtered = filt.filter(text)
            deduped = deduplicate(filtered.text, max_adjacent=3)
            truncated = smart_truncate(deduped, max_lines=100)
            return truncated.text