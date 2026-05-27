"""Keyword extraction for user prompts (L1 memory storage).

Extracts task intent keywords from user prompts for natural-language storage.
Uses pattern-based detection to identify the user's intent/task type.
"""

from __future__ import annotations

import re
from typing import Optional


# Intent patterns — matched case-insensitively
_INTENT_PATTERNS: list[tuple[str, list[re.Pattern]]] = [
    ("error", [
        re.compile(r"\berror\b", re.I),
        re.compile(r"\bfailed\b", re.I),
        re.compile(r"\bcrash\b", re.I),
        re.compile(r"\bbug\b", re.I),
        re.compile(r"\bexception\b", re.I),
        re.compile(r"\btraceback\b", re.I),
        re.compile(r"\bpanicked?\b", re.I),
    ]),
    ("implementation", [
        re.compile(r"\bimplement\b", re.I),
        re.compile(r"\badd\b", re.I),
        re.compile(r"\bcreate\b", re.I),
        re.compile(r"\bwrite\b", re.I),
        re.compile(r"\bbuild\b", re.I),
        re.compile(r"\bdevelop\b", re.I),
    ]),
    ("refactoring", [
        re.compile(r"\brefactor\b", re.I),
        re.compile(r"\brestructure\b", re.I),
        re.compile(r"\bimprove\b", re.I),
        re.compile(r"\boptimize\b", re.I),
        re.compile(r"\brewrite\b", re.I),
    ]),
    ("research", [
        re.compile(r"\bfind\b", re.I),
        re.compile(r"\bsearch\b", re.I),
        re.compile(r"\binvestigate\b", re.I),
        re.compile(r"\blook\s+for\b", re.I),
        re.compile(r"\bcheck\b", re.I),
        re.compile(r"\banalyze\b", re.I),
        re.compile(r"\bexplore\b", re.I),
    ]),
    ("documentation", [
        re.compile(r"\bdocument\b", re.I),
        re.compile(r"\bexplain\b", re.I),
        re.compile(r"\bdescribe\b", re.I),
        re.compile(r"\bcomment\b", re.I),
        re.compile(r"\bdocstring\b", re.I),
    ]),
    ("question", [
        re.compile(r"\bhow\s+do\s+I\b", re.I),
        re.compile(r"\bhow\s+can\s+I\b", re.I),
        re.compile(r"\bwhat\s+is\b", re.I),
        re.compile(r"\bwhy\s+does\b", re.I),
        re.compile(r"\bcan\s+you\b", re.I),
        re.compile(r"\bhelp\s+me\b", re.I),
        re.compile(r"\btell\s+me\b", re.I),
        re.compile(r"\bwhat\s+if\b", re.I),
    ]),
    ("code-review", [
        re.compile(r"\breview\b", re.I),
        re.compile(r"\baudit\b", re.I),
        re.compile(r"\bassess\b", re.I),
        re.compile(r"\bevalua", re.I),
    ]),
    ("debugging", [
        re.compile(r"\bdebug\b", re.I),
        re.compile(r"\bfix\b", re.I),
        re.compile(r"\bpatch\b", re.I),
        re.compile(r"\brepair\b", re.I),
        re.compile(r"\bsolve\b", re.I),
    ]),
    ("testing", [
        re.compile(r"\btest\b", re.I),
        re.compile(r"\bspec\b", re.I),
        re.compile(r"\bverify\b", re.I),
        re.compile(r"\bpytest\b", re.I),
        re.compile(r"\bunittest\b", re.I),
    ]),
    ("configuration", [
        re.compile(r"\bconfig(ure|uration)?\b", re.I),
        re.compile(r"\bsetup\b", re.I),
        re.compile(r"\binstall\b", re.I),
        re.compile(r"\bdeploy\b", re.I),
        re.compile(r"\benv(ironment)?\b", re.I),
    ]),
    ("git", [
        re.compile(r"\bcommit\b", re.I),
        re.compile(r"\bbranch\b", re.I),
        re.compile(r"\bmerge\b", re.I),
        re.compile(r"\brebase\b", re.I),
        re.compile(r"\bstash\b", re.I),
        re.compile(r"\bgit\b", re.I),
    ]),
    ("shell", [
        re.compile(r"\bshell\b", re.I),
        re.compile(r"\bcommand\s+line\b", re.I),
        re.compile(r"\bbash\b", re.I),
        re.compile(r"\bscript\b", re.I),
        re.compile(r"\bcli\b", re.I),
    ]),
]


def extract_user_prompt_keywords(text: str) -> str:
    """Extract task intent keywords from a user prompt.

    Scans the text for intent patterns and returns a comma-separated
    keyword string for natural-language memory storage.

    Args:
        text: The user prompt text (before or after Filter filtering)

    Returns:
        Comma-separated keywords, e.g. "error,debugging,implementation"
        Returns empty string if no keywords detected.
    """
    if not text or not text.strip():
        return ""

    found: list[str] = []
    for intent_name, patterns in _INTENT_PATTERNS:
        for pat in patterns:
            if pat.search(text):
                if intent_name not in found:
                    found.append(intent_name)
                break  # Move to next intent once one pattern matches

    # If we have no keyword match but the text is non-empty,
    # capture the first meaningful noun phrase (first 2-3 words as a fallback)
    if not found:
        words = text.strip().split()
        # Return first 3 significant words as a generic marker
        significant = [w for w in words[:5] if len(w) > 2 and w.isalpha()]
        if significant:
            return ",".join(significant[:3])
        return "general"

    return ",".join(found)


def extract_topic_from_prompt(text: str) -> Optional[str]:
    """Extract the primary topic/subject from a user prompt.

    Attempts to find a topic noun phrase near the beginning of the prompt.

    Args:
        text: The user prompt text

    Returns:
        The extracted topic string, or None if not determinable.
    """
    if not text:
        return None

    # Look for "I want to X the Y" or "X the Y" patterns
    patterns = [
        re.compile(r"\b(analyze|build|create|fix|implement|add|update|modify)\s+(the\s+)?(\w+)", re.I),
        re.compile(r"\b(working\s+on|project|file|module|function|class|api)\s+(\w+)", re.I),
    ]

    for pat in patterns:
        m = pat.search(text)
        if m:
            topic = m.group(3) if len(m.groups()) >= 3 else m.group(2) if len(m.groups()) >= 2 else m.group(1)
            if topic and len(topic) > 2:
                return topic

    return None
