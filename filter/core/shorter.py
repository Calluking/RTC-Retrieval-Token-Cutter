"""Unified context shortening primitives for memory integration.

Filter is NOT a compression tool - it does NOT encode/decode data.
Instead, it SHORTENS context length via Filter and format conversion,
while PRESERVING information density.

This module provides a single ShorterProtocol that wraps filter, dedup, truncate,
and summarize operations as composable stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from filter.core.dedup import deduplicate, deduplicate_with_grouping, DedupResult
from filter.core.filter import MinimalFilter, FilterResult
from filter.core.truncation import smart_truncate, smart_truncate_with_priority, TruncationResult
from filter.core.summarizer import summarize_generic, SummaryResult


@dataclass
class ShortenResult:
    """Result of a context shortening operation."""
    text: str
    original_chars: int
    shortened_chars: int
    shortening_ratio: float  # 0.0 = fully shortened, 1.0 = no change
    stages_applied: list[str]

    @property
    def tokens_saved_estimate(self) -> int:
        """Estimate tokens saved at ~4 chars/token."""
        return max(0, (self.original_chars - self.shortened_chars)) // 4

    @property
    def preserved_information_density(self) -> bool:
        """Check if information density is preserved.

        A shortening preserves information density if:
        1. Core semantic content is intact
        2. Structural elements (errors, warnings, signatures) are preserved
        3. A human can still take the same action based on shortened text
        """
        return self.shortening_ratio >= 0.5  # At least 50% of original


class Shorter(Protocol):
    """Protocol for context shortening strategies."""

    def shorten(self, text: str) -> str:
        """Shorten text and return the result."""
        ...


@dataclass
class PipelineShorter:
    """Composable context shortening pipeline.

    SHORTENS (does not compress) context via filter → dedup → truncate → summarize.
    Each stage is optional (None = skip).

    Key difference from compression:
    - Compression: encodes data to reduce size, reversible
    - Shortening: filters/transforms to reduce length, usually irreversible
    """

    filter_stage: MinimalFilter | None = None
    dedup_enabled: bool = True
    dedup_grouping_enabled: bool = False  # Enable error/warning grouping
    truncate_max_lines: int | None = None
    truncate_head: int | None = None
    truncate_tail: int = 10
    summarize_enabled: bool = False
    summarize_max_lines: int = 50

    def shorten(self, text: str, language: str | None = None) -> ShortenResult:
        """Apply shortening pipeline to text.

        Args:
            text: Input text to shorten
            language: Optional language hint for filter

        Returns:
            ShortenResult with shortened text and stats
        """
        original_chars = len(text)
        stages_applied: list[str] = []
        result = text

        # Stage 1: Filter (strips comments, normalizes whitespace)
        if self.filter_stage is not None:
            fr = self.filter_stage.filter(result, language)
            if fr.filtered_lines < fr.original_lines:
                result = fr.text
                stages_applied.append("filter")

        # Stage 2: Deduplication (collapses repeated lines)
        if self.dedup_enabled:
            before_dedup = len(result)
            if self.dedup_grouping_enabled:
                dedup_result = deduplicate_with_grouping(result)
                result = dedup_result.text
                if dedup_result.collapsed_repeats > 0:
                    stages_applied.append(f"dedup_{dedup_result.grouping_type}")
            else:
                result = deduplicate(result)
                if len(result) < before_dedup:
                    stages_applied.append("dedup")

        # Stage 3: Truncation (head + tail + marker)
        if self.truncate_max_lines is not None:
            tr = smart_truncate(
                result,
                max_lines=self.truncate_max_lines,
                head_lines=self.truncate_head,
                tail_lines=self.truncate_tail,
            )
            if tr.truncated_count > 0:
                result = tr.text
                stages_applied.append("truncate")

        # Stage 4: Summarization (head + tail + errors + warnings)
        if self.summarize_enabled:
            sr = summarize_generic(result, max_lines=self.summarize_max_lines)
            if sr.saved_tokens_estimate > 0:
                result = sr.text
                stages_applied.append("summarize")

        shortened_chars = len(result)
        ratio = shortened_chars / original_chars if original_chars > 0 else 1.0

        return ShortenResult(
            text=result,
            original_chars=original_chars,
            shortened_chars=shortened_chars,
            shortening_ratio=ratio,
            stages_applied=stages_applied,
        )


# Pre-built shorter presets for different use cases

def make_code_shorter(max_lines: int = 80) -> PipelineShorter:
    """Shorter for code output — strips comments, keeps structure."""
    return PipelineShorter(
        filter_stage=MinimalFilter(),
        dedup_enabled=True,
        truncate_max_lines=max_lines,
        truncate_tail=15,
        summarize_enabled=False,
    )


def make_log_shorter(max_lines: int = 100) -> PipelineShorter:
    """Shorter for log output — head + errors/warnings + tail."""
    return PipelineShorter(
        filter_stage=None,  # Don't strip comments in logs
        dedup_enabled=True,
        truncate_max_lines=None,
        summarize_enabled=True,
        summarize_max_lines=max_lines,
    )


def make_generic_shorter(max_lines: int = 60) -> PipelineShorter:
    """General-purpose shorter for arbitrary text."""
    return PipelineShorter(
        filter_stage=MinimalFilter(),
        dedup_enabled=True,
        truncate_max_lines=max_lines,
        truncate_tail=10,
        summarize_enabled=True,
        summarize_max_lines=max_lines,
    )


def make_memory_shorter(max_chars: int = 2000) -> PipelineShorter:
    """Shorter for memory context — aggressive but preserves signal.

    Used in memory pipeline to shorten retrieved blocks and
    session state before sending to LLM.
    """
    return PipelineShorter(
        filter_stage=MinimalFilter(),
        dedup_enabled=True,
        dedup_grouping_enabled=True,  # Enable error/warning grouping
        truncate_max_lines=None,  # Use char-based truncation instead
        summarize_enabled=True,
        summarize_max_lines=40,
    )


# Backward-compatible wrappers

def shorten_text(
    text: str,
    mode: str = "generic",
    max_lines: int | None = None,
) -> str:
    """Shorten text using preset modes.

    Args:
        text: Input text
        mode: One of "code", "log", "generic", "memory"
        max_lines: Optional override for max lines

    Returns:
        Shortened text (NOT compressed - no encoding involved)
    """
    shorters = {
        "code": make_code_shorter,
        "log": make_log_shorter,
        "generic": make_generic_shorter,
        "memory": make_memory_shorter,
    }
    shorter = shorters.get(mode, make_generic_shorter)()
    if max_lines is not None:
        shorter.truncate_max_lines = max_lines
    return shorter.shorten(text).text
