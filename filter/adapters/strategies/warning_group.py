"""WarningGroup — fold equivalent warnings by template + count."""

from __future__ import annotations

import re
from typing import Any

from filter.core.shorter import ShortenResult


_DEFAULT_WARNING_CLASSES = [
    r"\bDeprecationWarning\b",
    r"\bFutureWarning\b",
    r"\bUserWarning\b",
    r"\bRuntimeWarning\b",
    r"\bPendingDeprecationWarning\b",
    r"\bAstropyDeprecationWarning\b",
    r"\bAstropyUserWarning\b",
    r"\bConvergenceWarning\b",
    r"\bSyntaxWarning\b",
]
_DEFAULT_NORMALIZERS = [
    (re.compile(r"^/[^\s:]+:\d+:"), ":<PATH>:<N>:"),
    (re.compile(r"\d+\.\d+(\.\d+)?"), "<VER>"),
]


class WarningGroupStrategy:
    name = "warning_group"

    def shorten(self, text: str, cfg: dict[str, Any]) -> ShortenResult:
        original = len(text)
        classes = [re.compile(p) for p in cfg.get("warning_classes", _DEFAULT_WARNING_CLASSES)]
        normalizers = [
            (re.compile(p), repl) for p, repl in cfg.get("normalize_patterns", []) or _DEFAULT_NORMALIZERS
        ]
        seen: dict[str, list[int]] = {}
        out_lines: list[str] = []
        for idx, line in enumerate(text.splitlines()):
            is_warn = any(c.search(line) for c in classes)
            if not is_warn:
                out_lines.append(line)
                continue
            key = line
            for pat, repl in normalizers:
                key = pat.sub(repl, key)
            if key in seen:
                seen[key].append(idx)
                continue
            seen[key] = [idx]
            out_lines.append(line)
        extra: list[str] = []
        for key, indices in seen.items():
            if len(indices) > 1:
                extra.append(f"// warning_group: {len(indices) - 1} more equivalent occurrence(s) of warning template")
        if extra:
            out_lines.extend(extra)
        out = "\n".join(out_lines)
        return ShortenResult(
            text=out, original_chars=original, shortened_chars=len(out),
            shortening_ratio=len(out) / original if original else 1.0,
            stages_applied=["warning_group"],
        )