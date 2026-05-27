"""PythonSkeleton — AST-based skeleton extraction with regex-fallback for slices."""

from __future__ import annotations

from typing import Any

from filter.core.code_skeleton import (
    extract_python_skeleton,
    extract_python_slice_skeleton,
)
from filter.core.shorter import ShortenResult


class PythonSkeletonStrategy:
    name = "python_skeleton"

    def shorten(self, text: str, cfg: dict[str, Any]) -> ShortenResult:
        keep_docstrings = bool(cfg.get("keep_docstrings", True))
        slice_threshold = float(cfg.get("slice_threshold", 0.80))

        skel = extract_python_skeleton(text, keep_docstrings=keep_docstrings)
        if skel.fallback_reason is None:
            return ShortenResult(
                text=skel.text,
                original_chars=skel.original_chars,
                shortened_chars=skel.shortened_chars,
                shortening_ratio=skel.shortening_ratio,
                stages_applied=["python_skeleton"],
            )

        slice_skel = extract_python_slice_skeleton(text)
        if slice_skel.original_chars > 0 and slice_skel.shortening_ratio < slice_threshold:
            return ShortenResult(
                text=slice_skel.text,
                original_chars=slice_skel.original_chars,
                shortened_chars=slice_skel.shortened_chars,
                shortening_ratio=slice_skel.shortening_ratio,
                stages_applied=["python_slice_skeleton"],
            )

        return ShortenResult(
            text=skel.text,
            original_chars=skel.original_chars,
            shortened_chars=skel.shortened_chars,
            shortening_ratio=skel.shortening_ratio,
            stages_applied=[],
        )