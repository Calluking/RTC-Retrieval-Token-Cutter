"""LintGroup — group linter violations by rule-id, sample first N."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from filter.core.shorter import ShortenResult


_DEFAULT_PATTERN = re.compile(
    r"^(?P<path>[^:]+):(?P<line>\d+)(?::\d+)?:\s+(?P<code>[A-Z]\d{2,4}|error|warning|note|TS\d+)"
)
_DEFAULT_PASSTHROUGH = [
    r"^Your code has been rated",
    r"^Found \d+ error",
    r"^All checks passed",
    r"^\d+ files? checked",
]


class LintGroupStrategy:
    name = "lint_group"

    def shorten(self, text: str, cfg: dict[str, Any]) -> ShortenResult:
        original = len(text)
        pat = re.compile(cfg["line_pattern"]) if cfg.get("line_pattern") else _DEFAULT_PATTERN
        sample_per = int(cfg.get("sample_per_rule", 3))
        passthrough = [re.compile(p) for p in cfg.get("passthrough_patterns", _DEFAULT_PASSTHROUGH)]

        groups: dict[str, list[str]] = defaultdict(list)
        kept_verbatim: list[str] = []
        unmatched: list[str] = []

        for line in text.splitlines():
            if any(p.search(line) for p in passthrough):
                kept_verbatim.append(line)
                continue
            m = pat.search(line)
            if m:
                code = m.group("code")
                groups[code].append(line)
            else:
                unmatched.append(line)

        if not groups:
            return ShortenResult(
                text=text, original_chars=original, shortened_chars=original,
                shortening_ratio=1.0, stages_applied=[],
            )

        out: list[str] = []
        out.extend(unmatched[:5])
        for code in sorted(groups.keys()):
            lines = groups[code]
            out.append(f"// lint_group [{code}] {len(lines)} violation(s):")
            out.extend(lines[:sample_per])
            if len(lines) > sample_per:
                out.append(f"//   ... {len(lines) - sample_per} more [{code}] omitted")
        out.extend(kept_verbatim)
        result = "\n".join(out)
        return ShortenResult(
            text=result, original_chars=original, shortened_chars=len(result),
            shortening_ratio=len(result) / original if original else 1.0,
            stages_applied=["lint_group"],
        )