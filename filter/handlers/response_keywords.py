"""Response keyword extraction for LLM outputs (L1 memory storage).

Extracts keywords from LLM/agent responses based on detected output subtype
(patch, reasoning, error, tool_call, code, generic). Keywords are stored
as the overview field in natural-language entries.
"""

from __future__ import annotations

import re
from typing import Optional


# Patterns for subtype detection
_PATCH_PATTERNS = [
    re.compile(r"^--- a/", re.M),
    re.compile(r"^\+\+\+ b/", re.M),
    re.compile(r"^diff --git", re.M),
    re.compile(r"^@@\s+-\d+(?:,\d+)?\s+\+\d+(?:,\d+)?\s+@@", re.M),
]

_TOOL_CALL_PATTERNS = [
    re.compile(r"^<tool_call>", re.M),
    re.compile(r"^Calling tool:", re.M),
    re.compile(r'"name":\s*"(\w+)"', re.M),
]

_ERROR_PATTERNS = [
    re.compile(r"\b(Error|Exception|Failed|error|SEVERE|FATAL)\b", re.I),
    re.compile(r"Traceback \(most recent call last\)", re.M),
]

_REASONING_PATTERNS = [
    re.compile(r"^Let me think", re.M),
    re.compile(r"^First,? I", re.M),
    re.compile(r"^In summary,?", re.M),
    re.compile(r"^Therefore,?", re.M),
    re.compile(r"^The answer is", re.M),
    re.compile(r"^Step \d+[\.:]\s", re.M),
    re.compile(r"^\d+\.\s+[A-Z]", re.M),
]


def _detect_subtype(text: str) -> str:
    """Detect the subtype of LLM output for keyword extraction."""
    first_500 = text[:500]

    # Patch/diff — highest priority
    if _PATCH_PATTERNS[0].search(text) or _PATCH_PATTERNS[1].search(text):
        return "patch"
    if "diff --git" in text:
        return "patch"

    # Tool calls
    if "<tool_call>" in text or "Calling tool:" in first_500:
        return "tool_call"
    if '"name":' in first_500 and '"arguments":' in first_500:
        return "tool_call"

    # Error traces
    if "Traceback (most recent call last)" in text:
        return "error"
    if re.search(r"\b(Error|Exception|Failed|failed|error|SEVERE)\b", first_500):
        return "error"

    # Reasoning
    reasoning_count = sum(1 for p in _REASONING_PATTERNS if p.search(first_500))
    if reasoning_count >= 1 and len(text) > 500:
        return "reasoning"

    return "generic"


def _extract_patch_keywords(text: str) -> str:
    """Extract file paths from patch/diff output."""
    files = set()
    for m in re.finditer(r"^--- a/(\S+)", text, re.M):
        files.add(m.group(1))
    for m in re.finditer(r"^\+\+\+ b/(\S+)", text, re.M):
        files.add(m.group(1))
    if files:
        return "patch," + ",".join(sorted(files)[:5])
    return "patch"


def _extract_error_keywords(text: str) -> str:
    """Extract error type and message from error output."""
    # Find the first error line
    lines = text.splitlines()
    error_line = None
    for line in lines[:15]:
        if re.search(r"\b(Error|Exception|Failed|SEVERE|FATAL)\b", line, re.I):
            error_line = line.strip()
            break

    if error_line:
        # Extract the error type (first word(s) before the message)
        m = re.match(r"(\w+Error|\w+Exception|\w+Failed|Error|Exception|Failed):\s*(.*)", error_line)
        if m:
            error_type = m.group(1)
            error_msg = m.group(2)[:50] if m.group(2) else ""
            if error_msg:
                return f"error,{error_type},{error_msg}"
            return f"error,{error_type}"

    # Fallback: just mark as error
    return "error"


def _extract_reasoning_keywords(text: str) -> str:
    """Extract step topics from reasoning output."""
    keywords = ["reasoning"]
    lines = text.splitlines()

    # Collect first 3 step-like lines
    steps = []
    for line in lines[:20]:
        if re.match(r"^\s*(\d+\.|Step \d+|#\s|\-\s+)", line):
            step_text = re.sub(r"^\s*(\d+\.|Step \d+|#\s|\-\s+)\s*", "", line).strip()
            if step_text and len(step_text) > 3:
                steps.append(step_text[:40])
            if len(steps) >= 3:
                break

    if steps:
        keywords.extend(steps[:3])

    # Last step summary
    for line in lines[-5:]:
        stripped = line.strip()
        if stripped and len(stripped) > 3:
            keywords.append(stripped[:40])
            break

    return ",".join(keywords)


def _extract_tool_call_keywords(text: str) -> str:
    """Extract tool name from tool call output."""
    # Try XML format
    m = re.search(r"<name>(\w+)</name>", text)
    if m:
        return f"tool_call,{m.group(1)}"

    # Try JSON format
    m = re.search(r'"name":\s*"(\w+)"', text)
    if m:
        return f"tool_call,{m.group(1)}"

    # Try "Calling tool: name" format
    m = re.search(r"Calling tool:\s*(\w+)", text)
    if m:
        return f"tool_call,{m.group(1)}"

    return "tool_call"


def _extract_code_keywords(text: str) -> str:
    """Extract function/class signatures from code output."""
    keywords = ["code"]
    sig_lines = []

    # Look for function/class definitions
    for line in text.splitlines()[:30]:
        m = re.match(r"^\s*(async\s+)?(def|class)\s+(\w+)", line)
        if m:
            kind = m.group(2)
            name = m.group(3)
            sig_lines.append(f"{kind}:{name}")
        # Also capture decorated functions
        m2 = re.match(r"^\s*@(\w+)", line)
        if m2:
            sig_lines.append(f"decorator:{m2.group(1)}")

    if sig_lines:
        keywords.extend(sig_lines[:5])

    return ",".join(keywords)


def _extract_generic_keywords(text: str) -> str:
    """Extract keywords from generic text using simple heuristics."""
    if not text:
        return "generic"

    keywords = ["generic"]
    lines = text.splitlines()

    # First non-empty line as primary content indicator
    for line in lines[:5]:
        stripped = line.strip()
        if stripped and len(stripped) > 5:
            # Take first significant phrase (first 3-5 words)
            words = stripped.split()[:5]
            phrase = " ".join(w for w in words if len(w) > 2)[:50]
            if phrase:
                keywords.append(phrase)
            break

    # Look for any all-caps meaningful terms (constants, acronyms)
    for line in lines[:20]:
        for m in re.finditer(r"\b[A-Z]{2,}\b", line):
            term = m.group(0)
            if term not in ("I", "A", "API", "URL", "ID", "LLM"):
                keywords.append(term)
                break
        if len(keywords) >= 4:
            break

    return ",".join(keywords[:5])


def extract_response_keywords(text: str) -> str:
    """Extract keywords from an LLM/agent response for natural-language storage.

    Detects the response subtype (patch/reasoning/error/tool_call/code/generic)
    and extracts relevant keywords accordingly.

    Args:
        text: The raw LLM response text

    Returns:
        Comma-separated keyword string for the natural-language overview field.
        Returns "generic" for empty text.
    """
    if not text or not text.strip():
        return "generic"

    subtype = _detect_subtype(text)

    if subtype == "patch":
        return _extract_patch_keywords(text)
    elif subtype == "error":
        return _extract_error_keywords(text)
    elif subtype == "reasoning":
        return _extract_reasoning_keywords(text)
    elif subtype == "tool_call":
        return _extract_tool_call_keywords(text)
    elif subtype == "code":
        return _extract_code_keywords(text)
    else:
        return _extract_generic_keywords(text)
