"""Core types for the Filter adapter registry."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from filter.core.shorter import ShortenResult


class Strategy(Protocol):
    """A strategy shortens text under a profile-supplied config."""

    name: str  # e.g. "test_runner"

    def shorten(self, text: str, cfg: dict[str, Any]) -> ShortenResult:
        """Apply the strategy. Must be safe on input that doesn't match expectations."""
        ...


@dataclass(frozen=True)
class LibraryProfile:
    """Per-command / per-library routing entry."""
    name: str
    strategy_name: str
    command_hints: tuple[str, ...] = ()
    detect_patterns: tuple[re.Pattern, ...] = ()
    path_hints: tuple[str, ...] = ()
    category_hints: tuple[str, ...] = ()
    config: dict[str, Any] = field(default_factory=dict)
    priority: int = 50


@dataclass(frozen=True)
class AdapterMatch:
    """Result of route(): which profile won and at what score."""
    profile: LibraryProfile | None
    score: int
    strategy: Strategy | None
    reasons: tuple[str, ...] = ()

    @property
    def matched(self) -> bool:
        return self.profile is not None and self.strategy is not None


SCORE_COMMAND_EXACT = 100
SCORE_CATEGORY_HIT = 80
SCORE_PATTERN_HIT = 50
SCORE_PATH_EXT_HIT = 30
SCORE_THRESHOLD = 30