"""RequestLog — drop per-request access logs, keep exceptions."""

from __future__ import annotations

import re
from typing import Any

from filter.core.shorter import ShortenResult


_DEFAULT_ACCESS = [
    r"^\d+\.\d+\.\d+\.\d+ - - \[",
    r"\"(GET|POST|PUT|DELETE|HEAD|OPTIONS|PATCH) ",
    r"^[A-Z][a-z]+ HTTP/\d",
]
_DEFAULT_PRESERVE = [
    r"Traceback \(most recent call last\)",
    r"Exception",
    r"\b5\d\d\b",
    r"ERROR",
]


class RequestLogStrategy:
    name = "request_log"

    def shorten(self, text: str, cfg: dict[str, Any]) -> ShortenResult:
        original = len(text)
        access = [re.compile(p) for p in cfg.get("access_patterns", _DEFAULT_ACCESS)]
        preserve = [re.compile(p) for p in cfg.get("preserve_patterns", _DEFAULT_PRESERVE)]
        out_lines: list[str] = []
        dropped = 0
        for line in text.splitlines():
            if any(p.search(line) for p in preserve):
                out_lines.append(line)
                continue
            if any(a.search(line) for a in access):
                dropped += 1
                continue
            out_lines.append(line)
        if dropped:
            out_lines.append(f"// request_log: {dropped} access-log line(s) dropped")
        out = "\n".join(out_lines)
        return ShortenResult(
            text=out, original_chars=original, shortened_chars=len(out),
            shortening_ratio=len(out) / original if original else 1.0,
            stages_applied=["request_log"],
        )