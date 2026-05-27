"""PipProgress — drop pip's "Requirement already satisfied" / download spam."""

from __future__ import annotations

import re
from typing import Any

from filter.core.shorter import ShortenResult


_DEFAULT_DROP = [
    r"^Requirement already satisfied:",
    r"^Collecting ",
    r"^\s*Downloading ",
    r"^\s*Using cached ",
    r"^\s*Preparing metadata",
    r"^\s*Building wheel",
    r"^\s*Created wheel",
    r"^\s*Stored in directory",
    r"^\s*\|.*\|.*kB",
]
_DEFAULT_KEEP = [
    r"^Successfully installed",
    r"^Successfully uninstalled",
    r"^ERROR",
    r"^WARNING",
    r"^\s*ERROR",
    r"package needs to be reinstalled",
    r"Could not find",
]


class PipProgressStrategy:
    name = "pip_progress"

    def shorten(self, text: str, cfg: dict[str, Any]) -> ShortenResult:
        original = len(text)
        drop = [re.compile(p) for p in cfg.get("drop_patterns", _DEFAULT_DROP)]
        keep = [re.compile(p) for p in cfg.get("keep_patterns", _DEFAULT_KEEP)]
        out: list[str] = []
        dropped = 0
        for line in text.splitlines():
            if any(k.search(line) for k in keep):
                out.append(line)
                continue
            if any(d.search(line) for d in drop):
                dropped += 1
                continue
            out.append(line)
        if dropped:
            out.append(f"// pip_progress: {dropped} download/satisfied line(s) dropped")
        result = "\n".join(out)
        return ShortenResult(
            text=result, original_chars=original, shortened_chars=len(result),
            shortening_ratio=len(result) / original if original else 1.0,
            stages_applied=["pip_progress"],
        )