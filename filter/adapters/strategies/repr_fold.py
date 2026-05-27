"""ReprFold — head/tail-truncate large object reprs."""

from __future__ import annotations

import re
from typing import Any

from filter.core.shorter import ShortenResult


class ReprFoldStrategy:
    name = "repr_fold"

    def shorten(self, text: str, cfg: dict[str, Any]) -> ShortenResult:
        original = len(text)
        starts = [re.compile(p) for p in cfg.get("repr_starts", [])]
        ends = [re.compile(p) for p in cfg.get("repr_ends", [])]
        head_n = int(cfg.get("head_lines", 8))
        tail_n = int(cfg.get("tail_lines", 3))
        threshold = int(cfg.get("threshold_lines", 15))

        lines = text.splitlines()
        out: list[str] = []
        i = 0
        folded_blocks = 0
        while i < len(lines):
            line = lines[i]
            if not any(s.search(line) for s in starts):
                out.append(line)
                i += 1
                continue
            block_start = i
            j = i + 1
            while j < len(lines):
                if ends and any(e.search(lines[j]) for e in ends):
                    j += 1
                    break
                if not ends and lines[j].strip() == "":
                    break
                j += 1
            block = lines[block_start:j]
            if len(block) > threshold:
                out.extend(block[:head_n])
                out.append(f"// ... repr_fold: {len(block) - head_n - tail_n} line(s) elided ...")
                out.extend(block[-tail_n:] if tail_n > 0 else [])
                folded_blocks += 1
            else:
                out.extend(block)
            i = j
        result = "\n".join(out)
        return ShortenResult(
            text=result, original_chars=original, shortened_chars=len(result),
            shortening_ratio=len(result) / original if original else 1.0,
            stages_applied=["repr_fold"] if folded_blocks else [],
        )