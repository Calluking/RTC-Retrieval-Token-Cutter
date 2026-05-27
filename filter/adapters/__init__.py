"""Filter adapter registry and strategies."""

from filter.adapters.base import (
    AdapterMatch,
    LibraryProfile,
    Strategy,
    SCORE_CATEGORY_HIT,
    SCORE_COMMAND_EXACT,
    SCORE_PATH_EXT_HIT,
    SCORE_PATTERN_HIT,
    SCORE_THRESHOLD,
)
from filter.adapters.registry import route

__all__ = [
    "AdapterMatch",
    "LibraryProfile",
    "Strategy",
    "route",
    "SCORE_CATEGORY_HIT",
    "SCORE_COMMAND_EXACT",
    "SCORE_PATH_EXT_HIT",
    "SCORE_PATTERN_HIT",
    "SCORE_THRESHOLD",
]