"""DiffHunk — preserve unified-diff hunks, drop excessive unchanged context."""

from __future__ import annotations

import re
from typing import Any

from filter.core.shorter import ShortenResult


_FILE_HEADER = re.compile(r"^(diff --git|--- [ab]/|\+\+\+ [ab]/|index [0-9a-f]+\.\.)")
_HUNK_HEADER = re.compile(r"^@@\s+-\d+(?:,\d+)?\s+\+\d+(?:,\d+)?\s+@@")


class DiffHunkStrategy:
    name = "diff_hunk"

    def shorten(self, text: str, cfg: dict[str, Any]) -> ShortenResult:
        original = len(text)
        ctx = int(cfg.get("context_window", 3))

        lines = text.splitlines()
        out: list[str] = []
        keep = [False] * len(lines)
        for i, line in enumerate(lines):
            if _FILE_HEADER.match(line) or _HUNK_HEADER.match(line):
                keep[i] = True
                continue
            if line.startswith(("+", "-")) and not line.startswith(("+++", "---")):
                for j in range(max(0, i - ctx), min(len(lines), i + ctx + 1)):
                    keep[j] = True

        i = 0
        gap = 0
        while i < len(lines):
            if keep[i]:
                if gap > 0:
                    out.append(f"  // diff_hunk: {gap} unchanged context line(s) elided")
                    gap = 0
                out.append(lines[i])
            else:
                gap += 1
            i += 1
        if gap > 0:
            out.append(f"  // diff_hunk: {gap} unchanged context line(s) elided")
        result = "\n".join(out)
        return ShortenResult(
            text=result, original_chars=original, shortened_chars=len(result),
            shortening_ratio=len(result) / original if original else 1.0,
            stages_applied=["diff_hunk"],
        )