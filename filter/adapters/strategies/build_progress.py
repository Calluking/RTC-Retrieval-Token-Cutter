"""BuildProgress — drop progress chatter, keep warn/error/summary."""

from __future__ import annotations

import re
from typing import Any

from filter.core.shorter import ShortenResult


class BuildProgressStrategy:
    name = "build_progress"

    def shorten(self, text: str, cfg: dict[str, Any]) -> ShortenResult:
        original = len(text)
        drop = [re.compile(p) for p in cfg.get("drop_patterns", [])]
        keep = [re.compile(p) for p in cfg.get("keep_patterns", [])]
        out_lines: list[str] = []
        dropped = 0
        for line in text.splitlines():
            if keep:
                if any(k.search(line) for k in keep):
                    out_lines.append(line)
                else:
                    dropped += 1
                continue
            if any(d.search(line) for d in drop):
                dropped += 1
                continue
            out_lines.append(line)
        if dropped:
            out_lines.append(f"// build_progress: {dropped} progress line(s) dropped")
        out = "\n".join(out_lines)
        return ShortenResult(
            text=out, original_chars=original, shortened_chars=len(out),
            shortening_ratio=len(out) / original if original else 1.0,
            stages_applied=["build_progress"],
        )