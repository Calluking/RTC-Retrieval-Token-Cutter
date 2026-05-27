"""SWE-bench problem statement compression — structure-aware."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class IssueRegion:
    kind: str  # "description" | "steps" | "expected" | "actual" | "error" | "code" | "other"
    content: str
    priority: int  # 0=highest (must keep), 10=lowest (discardable)
    original_len: int


# Patterns for content-type detection within description body
_ERROR_PATTERNS = re.compile(
    r"(Traceback|Error:|Exception:|raise\s+\w+Error|failed|Failed|timeout|crashed)",
    re.IGNORECASE,
)
_CODE_BLOCK_PATTERNS = re.compile(r"^```|^# .*\.(py|js|ts|go|java|cpp|c)$", re.MULTILINE)
_NUMBERED_STEP_PATTERNS = re.compile(r"^\s*\d+[\.\)]\s+\S", re.MULTILINE)


def _detect_inline_code_blocks(text: str) -> list[tuple[int, int]]:
    """Find start/end indices of inline code blocks (```...```).

    Returns list of (start, end) tuples.
    """
    blocks = []
    pattern = re.compile(r"```[\w]*\n.*?\n```", re.DOTALL)
    for m in pattern.finditer(text):
        blocks.append((m.start(), m.end()))
    return blocks


def extract_issue_regions(problem: str) -> list[IssueRegion]:
    """Split problem statement into semantic regions with priority.

    Priority mapping:
      0 = critical (error traces, expected/actual) — never discard
      1 = high (steps, code blocks) — preserve as much as possible
      2 = medium (description body) — compress if needed
      3 = low (version info, meta) — can discard under budget
    """
    # Match both ## and ### markdown headers
    header_patterns = [
        (re.compile(r"^#{2,3}\s*(description|描述)", re.IGNORECASE), "description", 2),
        (re.compile(r"^#{2,3}\s*(steps? to reproduce|复现步骤|how to reproduce)", re.IGNORECASE), "steps", 1),
        (re.compile(r"^#{2,3}\s*(expected|期望|expected behavior)", re.IGNORECASE), "expected", 0),
        (re.compile(r"^#{2,3}\s*(actual|实际|actual behavior|observed)", re.IGNORECASE), "actual", 0),
        (re.compile(r"^#{2,3}\s*(error|错误|stack\s*trace|error log)", re.IGNORECASE), "error", 0),
        (re.compile(r"^#{2,3}\s*(environment|版本|versions?|system)", re.IGNORECASE), "other", 3),
        (re.compile(r"^#{2,3}\s*", re.IGNORECASE), "other", 2),
    ]

    regions: list[IssueRegion] = []
    current_kind = "description"
    current_priority = 2
    current_lines: list[str] = []

    def _flush(kind: str, priority: int, lines: list[str]) -> None:
        if lines:
            content = "\n".join(lines).strip()
            if content:
                regions.append(IssueRegion(
                    kind=kind,
                    content=content,
                    priority=priority,
                    original_len=len(content),
                ))

    for line in problem.splitlines():
        matched = False
        for pattern, kind, priority in header_patterns:
            if pattern.match(line):
                _flush(current_kind, current_priority, current_lines)
                current_kind = kind
                current_priority = priority
                current_lines = [line]
                matched = True
                break
        if not matched:
            current_lines.append(line)

    _flush(current_kind, current_priority, current_lines)
    return regions


def extract_structured_regions(problem: str) -> list[IssueRegion]:
    """Alternative extraction: detect content types from description body.

    For problem statements without markdown headers, detect:
    - Error/traceback sections (priority 0)
    - Numbered steps (priority 1)
    - Code blocks (priority 1)
    - Description paragraphs (priority 2)
    """
    # First pass: try header-based extraction
    regions = extract_issue_regions(problem)

    # Check if we got meaningful structure (multiple regions or non-trivial header)
    has_structure = len(regions) > 1 or any(
        r.kind in ("steps", "expected", "actual", "error") for r in regions
    )

    if has_structure:
        return regions

    # Fallback: content-type detection within description
    # Split by paragraphs, classify each
    new_regions: list[IssueRegion] = []
    paragraphs = re.split(r"\n\n+", problem)

    for para in paragraphs:
        if not para.strip():
            continue

        para_stripped = para.strip()
        priority = 2  # default

        # Detect if this paragraph contains error/traceback
        if _ERROR_PATTERNS.search(para):
            priority = 0
            kind = "error"
        # Detect if this looks like steps (numbered items)
        elif _NUMBERED_STEP_PATTERNS.search(para):
            priority = 1
            kind = "steps"
        # Detect code blocks within paragraph
        elif para_stripped.startswith("```") or "```python" in para_stripped or "```bash" in para_stripped:
            priority = 1
            kind = "code"
        else:
            kind = "description"

        new_regions.append(IssueRegion(
            kind=kind,
            content=para_stripped,
            priority=priority,
            original_len=len(para_stripped),
        ))

    return new_regions if new_regions else regions


def compress_code_block(block: str) -> str:
    """Smart compress code block: keep first/last 3 lines + structure.

    Code blocks in issue descriptions often show:
    - Environment setup (imports, configs) — at start
    - The bug demonstration — in middle
    - Error output — at end
    We preserve structure while collapsing long implementations.
    """
    lines = block.splitlines()
    if not lines:
        return block

    # Detect if this is a traceback (consecutive error lines)
    is_traceback = _is_traceback(lines)

    if is_traceback:
        if len(lines) > 12:
            head = lines[:5]
            tail = lines[-5:]
            marker = f"\n    // ... {len(lines) - 10} lines omitted ...\n"
            return "\n".join(head) + marker + "\n".join(tail)
        return block

    # For regular code: keep first 3, last 3, collapse middle
    if len(lines) > 8:
        head = lines[:3]
        tail = lines[-3:]
        marker = f"\n    // ... {len(lines) - 6} lines omitted ...\n"
        return "\n".join(head) + marker + "\n".join(tail)

    return block


def _is_traceback(lines: list[str]) -> bool:
    """Check if block looks like a traceback/error dump."""
    traceback_markers = ["  File ", "    in ", "Traceback (", "Error:", "Exception:"]
    match_count = sum(1 for line in lines[:8] if any(m in line for m in traceback_markers))
    return match_count >= 2


def compress_regions(regions: list[IssueRegion], budget_chars: int) -> str:
    """Compress regions within character budget, preserving high-priority ones.

    Strategy:
    1. Sort critical (priority 0) and high (priority 1) regions first
    2. Always include at least partial content from ALL regions (no discard)
    3. For each region, compress_code_block for code, truncate for text
    4. Fill remaining budget with lower priority content
    """
    if not regions:
        return ""

    # Sort by priority (lower = more important), then by length (shorter first)
    sorted_regions = sorted(regions, key=lambda r: (r.priority, r.original_len))

    result_parts: list[str] = []
    remaining = budget_chars

    # Phase 1: Critical (priority 0) regions — always get full or partial content
    for region in sorted_regions:
        if region.priority != 0:
            continue

        if region.kind == "code":
            content = compress_code_block(region.content)
        else:
            content = region.content

        if len(content) <= remaining:
            result_parts.append(content)
            remaining -= len(content)
        elif remaining > 0:
            result_parts.append(content[:remaining])
            remaining = 0

    # Phase 2: High priority (priority 1) regions — code blocks, steps
    for region in sorted_regions:
        if region.priority != 1:
            continue

        if region.kind == "code":
            content = compress_code_block(region.content)
        else:
            content = region.content

        if len(content) <= remaining:
            result_parts.append(content)
            remaining -= len(content)
        elif remaining > 0:
            # Always include at least something from priority 1
            result_parts.append(content[:remaining])
            remaining = 0

    # Phase 3: Medium priority (priority 2) — description body
    # Sort by position: earlier sections (first in doc) get filled first
    priority2 = [r for r in sorted_regions if r.priority == 2]
    # Re-sort priority 2 by original_len (shortest first, maximize coverage)
    priority2.sort(key=lambda r: r.original_len)

    for region in priority2:
        if remaining <= 0:
            break
        content = region.content
        if len(content) <= remaining:
            result_parts.append(content)
            remaining -= len(content)
        else:
            # Partial fill: keep head of description
            result_parts.append(content[:remaining])
            remaining = 0

    # Phase 4: Low priority (priority 3) — version info etc.
    for region in sorted_regions:
        if region.priority != 3:
            continue
        if remaining <= 0:
            break
        content = region.content
        if len(content) <= remaining:
            result_parts.append(content)
            remaining -= len(content)
        # Priority 3: skip if doesn't fit (acceptable)

    return "\n\n".join(result_parts)


def compress_swebench_problem(problem: str, budget_chars: int = 1500) -> str:
    """Main entry point: compress SWE-bench problem statement within budget.

    Args:
        problem: Original problem statement text
        budget_chars: Maximum characters to keep (default 1500)

    Returns:
        Compressed text that preserves critical information
    """
    if len(problem) <= budget_chars:
        return problem

    regions = extract_structured_regions(problem)
    return compress_regions(regions, budget_chars)


def get_region_summary(regions: list[IssueRegion]) -> dict:
    """Get a summary of regions for debugging."""
    return {
        "total_regions": len(regions),
        "by_priority": {
            p: [r.kind for r in regions if r.priority == p]
            for p in range(4)
        },
        "total_chars": sum(r.original_len for r in regions),
    }