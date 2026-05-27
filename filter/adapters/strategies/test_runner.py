"""TestRunner — fold passing test runs while keeping failures verbatim."""

from __future__ import annotations

import re
from typing import Any

from filter.core.log_template import fold_test_output
from filter.core.shorter import ShortenResult


def _drop_noise(text: str, patterns: list[str]) -> str:
    if not patterns:
        return text
    compiled = [re.compile(p) for p in patterns]
    keep: list[str] = []
    for line in text.splitlines():
        if any(c.search(line) for c in compiled):
            continue
        keep.append(line)
    return "\n".join(keep)


class TestRunnerStrategy:
    name = "test_runner"

    def shorten(self, text: str, cfg: dict[str, Any]) -> ShortenResult:
        original = len(text)
        cleaned = _drop_noise(text, cfg.get("noise_lines", []))
        fold = fold_test_output(cleaned)
        out = fold.text
        summary = (
            f"// test summary: {fold.passed_count} passed, "
            f"{fold.failed_count} failed, {fold.skipped_count} skipped"
        )
        if fold.passed_count + fold.failed_count + fold.skipped_count > 0:
            out = out + "\n" + summary
        return ShortenResult(
            text=out,
            original_chars=original,
            shortened_chars=len(out),
            shortening_ratio=len(out) / original if original else 1.0,
            stages_applied=["test_runner"],
        )