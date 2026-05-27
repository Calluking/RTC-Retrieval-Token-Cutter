from filter.core.filter import MinimalFilter, AggressiveFilter, FilterResult
from filter.core.truncation import smart_truncate, TruncationResult
from filter.core.dedup import deduplicate
from filter.core.registry import HandlerRegistry
from filter.core.shorter import (
    ShortenResult,
    Shorter,
    PipelineShorter,
    shorten_text,
    make_code_shorter,
    make_log_shorter,
    make_generic_shorter,
    make_memory_shorter,
)

__all__ = [
    # Core filter/transform primitives (RTK-style)
    "MinimalFilter",
    "AggressiveFilter",
    "FilterResult",
    "smart_truncate",
    "TruncationResult",
    "deduplicate",
    "HandlerRegistry",
    # Context shortening API (replaces "compression" terminology)
    "ShortenResult",
    "Shorter",
    "PipelineShorter",
    "shorten_text",
    "make_code_shorter",
    "make_log_shorter",
    "make_generic_shorter",
    "make_memory_shorter",
]