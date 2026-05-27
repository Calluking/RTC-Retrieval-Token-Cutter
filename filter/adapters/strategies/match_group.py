"""MatchGroup — group grep/rg output by file, sample first N hits per file."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from filter.core.shorter import ShortenResult


_DEFAULT_PATTERN = re.compile(r"^(?P<path>[^:\s][^:]*):(?P<lineno>\d+):")


class MatchGroupStrategy:
    name = "match_group"

    def shorten(self, text: str, cfg: dict[str, Any]) -> ShortenResult:
        original = len(text)
        sample_per = int(cfg.get("sample_per_file", 5))
        pat = re.compile(cfg["line_pattern"]) if cfg.get("line_pattern") else _DEFAULT_PATTERN

        by_file: dict[str, list[str]] = defaultdict(list)
        non_match: list[str] = []
        for line in text.splitlines():
            m = pat.match(line)
            if m:
                by_file[m.group("path")].append(line)
            else:
                non_match.append(line)

        if not by_file:
            return ShortenResult(
                text=text, original_chars=original, shortened_chars=original,
                shortening_ratio=1.0, stages_applied=[],
            )

        out: list[str] = []
        out.extend(non_match[:5])
        total_kept = 0
        total_dropped = 0
        for path in sorted(by_file.keys()):
            hits = by_file[path]
            out.append(f"// match_group {path}: {len(hits)} match(es)")
            out.extend(hits[:sample_per])
            total_kept += min(sample_per, len(hits))
            extra = max(0, len(hits) - sample_per)
            if extra:
                out.append(f"//   ... {extra} more match(es) in {path}")
                total_dropped += extra
        out.append(f"// match_group total: {total_kept} kept, {total_dropped} dropped, {len(by_file)} file(s)")
        result = "\n".join(out)
        return ShortenResult(
            text=result, original_chars=original, shortened_chars=len(result),
            shortening_ratio=len(result) / original if original else 1.0,
            stages_applied=["match_group"],
        )