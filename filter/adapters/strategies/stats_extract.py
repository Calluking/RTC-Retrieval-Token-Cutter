"""StatsExtract — collapse list-of-X output to category counts + sample."""

from __future__ import annotations

import re
from typing import Any

from filter.core.shorter import ShortenResult


class StatsExtractStrategy:
    name = "stats_extract"

    def shorten(self, text: str, cfg: dict[str, Any]) -> ShortenResult:
        original = len(text)
        sections: list[tuple[re.Pattern, int]] = [
            (re.compile(p), n) for p, n in cfg.get("sections", [])
        ]
        default_sample = int(cfg.get("default_sample", 5))

        lines = text.splitlines()
        out: list[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            matched_section = None
            for pat, n in sections:
                if pat.search(line):
                    matched_section = (pat, n)
                    break
            if matched_section is None:
                out.append(line)
                i += 1
                continue
            _, sample_n = matched_section
            out.append(line)
            i += 1
            body_start = i
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or lines[i].strip() == ""):
                if not lines[i].strip():
                    break
                i += 1
            body = lines[body_start:i]
            if len(body) <= sample_n:
                out.extend(body)
            else:
                out.extend(body[:sample_n])
                out.append(f"        // stats_extract: {len(body) - sample_n} more entry(ies) in this section")
            if i < len(lines) and lines[i].strip() == "":
                out.append(lines[i])
                i += 1
        result = "\n".join(out)
        return ShortenResult(
            text=result, original_chars=original, shortened_chars=len(result),
            shortening_ratio=len(result) / original if original else 1.0,
            stages_applied=["stats_extract"],
        )