"""TreeCondense — aggregate large directory listings by extension / depth."""

from __future__ import annotations

import os
import re
from collections import defaultdict
from typing import Any

from filter.core.shorter import ShortenResult


_PATHLIKE = re.compile(r"[/\w.\-]+")


def _looks_like_path(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if "/" in s:
        return True
    if "." in s.rsplit("/", 1)[-1]:
        return True
    return False


class TreeCondenseStrategy:
    name = "tree_condense"

    def shorten(self, text: str, cfg: dict[str, Any]) -> ShortenResult:
        original = len(text)
        threshold = int(cfg.get("threshold", 30))
        sample_per = int(cfg.get("sample_per_ext", 5))
        no_ext_label = cfg.get("no_ext_label", "<noext>")

        lines = text.splitlines()
        path_lines = [l for l in lines if _looks_like_path(l)]
        if len(path_lines) < threshold:
            return ShortenResult(
                text=text, original_chars=original, shortened_chars=original,
                shortening_ratio=1.0, stages_applied=[],
            )

        by_ext: dict[str, list[str]] = defaultdict(list)
        for line in path_lines:
            base = line.strip().rstrip("/").split()[-1]
            _, ext = os.path.splitext(base)
            key = ext.lower() if ext else no_ext_label
            by_ext[key].append(line)

        out: list[str] = []
        for line in lines:
            if not _looks_like_path(line):
                out.append(line)
        out.append("// tree_condense: per-extension summary")
        for ext in sorted(by_ext.keys()):
            grp = by_ext[ext]
            out.append(f"//   {ext} x {len(grp)}")
            out.extend(grp[:sample_per])
            if len(grp) > sample_per:
                out.append(f"//     ... {len(grp) - sample_per} more {ext} omitted")
        result = "\n".join(out)
        return ShortenResult(
            text=result, original_chars=original, shortened_chars=len(result),
            shortening_ratio=len(result) / original if original else 1.0,
            stages_applied=["tree_condense"],
        )