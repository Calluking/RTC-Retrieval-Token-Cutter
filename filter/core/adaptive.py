"""Adaptive context shortening — selects strategy based on content type.

Phase 3 of Filter implementation: automatically detect content type and
apply the optimal shortening strategy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Literal

from filter.core.shorter import (
    PipelineShorter,
    ShortenResult,
    make_code_shorter,
    make_log_shorter,
    make_generic_shorter,
    make_memory_shorter,
)


class ContentType(Enum):
    """Content type enumeration for adaptive shortening."""
    CODE = auto()
    LOG = auto()
    ERROR = auto()
    MEMORY = auto()
    GENERIC = auto()


@dataclass
class AdaptiveShortenResult:
    """Result of adaptive shortening operation."""
    text: str
    content_type: ContentType
    strategy_used: str
    original_chars: int
    shortened_chars: int
    shortening_ratio: float


# Content type detection patterns
_CODE_PATTERNS = [
    re.compile(r"^\s*(def|class|async\s+def|import|from|const|let|var|function)\s+", re.MULTILINE),
    re.compile(r"^\s*(if|else|elif|for|while|try|except|catch|switch)\s*[\({]?", re.MULTILINE),
    re.compile(r"^\s*#.*", re.MULTILINE),  # Comments in code
    re.compile(r"\{[\s\n]*\"[^\"]+\":", re.MULTILINE),  # JSON/object literals
]

_LOG_PATTERNS = [
    re.compile(r"^(?:\s*\d+\s+)?\d{4}-\d{2}-\d{2}[\sT]", re.MULTILINE),  # ISO date, optionally Read-numbered
    re.compile(r"^\[\s*(DEBUG|INFO|WARN|ERROR|FATAL)", re.MULTILINE),
    re.compile(r"^\[(summary|trace|failure|debug|info|warn|error|fatal)\]", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^(failure_count|function_count|expected_source)=", re.MULTILINE),
    re.compile(r"\b(log|print|echo|printf|console\.log)\s*\(", re.IGNORECASE),
    re.compile(r"^\s*at\s+[\w.$]+\([^)]*\)\s*$", re.MULTILINE),  # Stack trace lines
]

_LOG_LINE_PREFIX_PATTERN = re.compile(
    r"^\s*(?:\d+\s+)?(?:"
    r"\d{4}-\d{2}-\d{2}[\sT].*\b(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|TRACE)\b"
    r"|\[(summary|trace|failure|debug|info|warn|warning|error|fatal)\]"
    r")",
    re.MULTILINE,
)

_ERROR_PATTERNS = [
    re.compile(r"\b(ERROR|Error|error|SEVERE|FATAL|Exception|Failed)", re.IGNORECASE),
    re.compile(r"Traceback\s*\(most recent call last\)", re.MULTILINE),
    re.compile(r"^\s*File\s+\".*\",\s+line\s+\d+", re.MULTILINE),
    re.compile(r"\bFailed to\b", re.IGNORECASE),
]

_MEMORY_PATTERNS = [
    re.compile(r"^(Context|Memory|Archive|Overview|Abstract):", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^\s*-\s+[\w\s]+:", re.MULTILINE),  # Bullet points with labels
    re.compile(r"^\s*##\s+\w+", re.MULTILINE),  # Markdown headers
]


def detect_content_type(text: str) -> ContentType:
    """Detect the type of content for adaptive shortening strategy selection.

    Args:
        text: Input text to analyze

    Returns:
        ContentType enum value
    """
    if not text or len(text.strip()) < 10:
        return ContentType.GENERIC

    lines = text.splitlines()
    first_lines = "\n".join(lines[:20])  # Sample first 20 lines

    # Check for error patterns first (highest priority)
    error_matches = sum(1 for p in _ERROR_PATTERNS if p.search(text))
    if error_matches >= 2:
        return ContentType.ERROR

    # Check for code patterns
    code_matches = sum(1 for p in _CODE_PATTERNS if p.search(first_lines))
    if code_matches >= 3:
        return ContentType.CODE

    # Check for log patterns
    log_matches = sum(1 for p in _LOG_PATTERNS if p.search(first_lines))
    log_line_matches = len(_LOG_LINE_PREFIX_PATTERN.findall(first_lines))
    if log_matches >= 2 or log_line_matches >= 3:
        return ContentType.LOG

    # Check for memory/archive patterns
    memory_matches = sum(1 for p in _MEMORY_PATTERNS if p.search(first_lines))
    if memory_matches >= 2:
        return ContentType.MEMORY

    return ContentType.GENERIC


def get_shorter_for_type(content_type: ContentType, max_lines: int | None = None) -> PipelineShorter:
    """Get the appropriate PipelineShorter for a content type.

    Args:
        content_type: Detected content type
        max_lines: Optional max lines override

    Returns:
        Configured PipelineShorter instance
    """
    shorter_map = {
        ContentType.CODE: make_code_shorter,
        ContentType.LOG: make_log_shorter,
        ContentType.ERROR: make_log_shorter,  # Logs often contain errors
        ContentType.MEMORY: make_memory_shorter,
        ContentType.GENERIC: make_generic_shorter,
    }

    shorter_factory = shorter_map.get(content_type, make_generic_shorter)
    shorter = shorter_factory()

    if max_lines is not None:
        if content_type in (ContentType.LOG, ContentType.ERROR):
            shorter.summarize_max_lines = max_lines
        else:
            shorter.truncate_max_lines = max_lines

    return shorter


def adaptive_shorten(
    text: str,
    max_lines: int | None = None,
    preserve_critical: bool = True,
) -> AdaptiveShortenResult:
    """Adaptively shorten text by detecting content type and applying optimal strategy.

    This is Phase 3 of Filter implementation - using content type detection to
    automatically select the best shortening strategy.

    Args:
        text: Input text to shorten
        max_lines: Optional max lines for truncation
        preserve_critical: Whether to prioritize critical lines

    Returns:
        AdaptiveShortenResult with shortened text and metadata
    """
    original_chars = len(text)

    # Detect content type
    content_type = detect_content_type(text)

    # Get appropriate shorter for content type
    shorter = get_shorter_for_type(content_type, max_lines)

    # Apply shortening
    result = shorter.shorten(text)

    return AdaptiveShortenResult(
        text=result.text,
        content_type=content_type,
        strategy_used=content_type.name.lower(),
        original_chars=original_chars,
        shortened_chars=len(result.text),
        shortening_ratio=result.shortening_ratio,
    )


# Convenience functions for direct usage

def shorten_code(text: str, max_lines: int = 80) -> str:
    """Shorten code content with code-specific strategy."""
    return make_code_shorter(max_lines).shorten(text).text


def shorten_log(text: str, max_lines: int = 100) -> str:
    """Shorten log content with log-specific strategy."""
    return make_log_shorter(max_lines).shorten(text).text


def shorten_error(text: str, max_lines: int = 80) -> str:
    """Shorten error content, preserving error patterns."""
    return make_log_shorter(max_lines).shorten(text).text


def shorten_memory(text: str, max_chars: int = 2000) -> str:
    """Shorten memory content with memory-specific strategy."""
    shorter = make_memory_shorter(max_chars)
    return shorter.shorten(text).text
