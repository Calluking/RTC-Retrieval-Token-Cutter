"""Code and output filtering — strips comments, normalizes whitespace."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterator


# Languages / formats that should NEVER be filtered (body could be corrupted)
SAFE_FORMATS = frozenset({"json", "yaml", "yml", "toml", "xml", "html", "csv"})


@dataclass
class FilterResult:
    text: str
    original_lines: int
    filtered_lines: int
    removed_tokens_estimate: int


class MinimalFilter:
    """Strips line comments, block comments, normalizes blank lines.

    Safe for: Rust, Python, JS/TS, Go, C, C++, Ruby, Shell scripts.
    """

    LINE_COMMENTS = {
        "//": "rust,js,ts,go,c,cpp,java,swift,go",
        "#": "python,shell,ruby,yaml",
        "--": "sql,haskell",
    }

    _line_pattern: re.Pattern = re.compile(r"^\s*(//|#|--).*$")
    _block_start: re.Pattern = re.compile(r"/\*|\*/")
    _trailing_ws: re.Pattern = re.compile(r"[ \t]+$")

    def filter(self, text: str, language: str | None = None) -> FilterResult:
        if language and language.lower() in SAFE_FORMATS:
            return FilterResult(
                text=text,
                original_lines=len(text.splitlines()),
                filtered_lines=len(text.splitlines()),
                removed_tokens_estimate=0,
            )

        original_lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
        filtered_lines_out: list[str] = []
        removed = 0
        in_block = False

        for raw_line in text.splitlines():
            stripped = raw_line.lstrip()

            # Detect block comment boundaries (only for /* */ style)
            if stripped.startswith("/*"):
                in_block = True
                continue
            if stripped.startswith("*/"):
                in_block = False
                continue

            if in_block:
                continue

            # Line comments
            if stripped.startswith(("//", "#", "--")):
                removed += 1
                continue

            # Normalize trailing whitespace
            normalized = self._trailing_ws.sub("", raw_line)

            # Collapse consecutive blank lines to max 1
            if normalized.strip() == "":
                if filtered_lines_out and filtered_lines_out[-1].strip() == "":
                    continue
                filtered_lines_out.append("")
            else:
                filtered_lines_out.append(normalized)

        result = "\n".join(filtered_lines_out).strip("\n")
        removed_tokens_estimate = removed * 2  # rough estimate
        return FilterResult(
            text=result,
            original_lines=original_lines,
            filtered_lines=len(filtered_lines_out),
            removed_tokens_estimate=removed_tokens_estimate,
        )


class AggressiveFilter(MinimalFilter):
    """Extends MinimalFilter: also strips function bodies, keeps signatures/imports.

    Use for: code review, diff review, or when you only need structural overview.
    """

    _func_sig: re.Pattern = re.compile(
        r"^(def |fn |func |function |class |struct |enum |impl |pub |import |use |from |const |static |async |async fn |->|interface |module )"
    )

    def filter(self, text: str, language: str | None = None) -> FilterResult:
        base = super().filter(text, language)
        original_lines = base.original_lines
        lines = base.text.splitlines()
        kept: list[str] = []
        skipped = 0

        i = 0
        while i < len(lines):
            line = lines[i]
            # Always keep lines that look like declarations/signatures
            if self._func_sig.match(line.lstrip()):
                kept.append(line)
                i += 1
                continue

            # Skip function body lines (indented relative to declaration)
            stripped = line.lstrip()
            if stripped and not stripped.startswith("#") and line.startswith(" ") or line.startswith("\t"):
                # Inside a block — skip until dedented
                skipped += 1
                i += 1
                continue

            kept.append(line)
            i += 1

        result = "\n".join(kept)
        return FilterResult(
            text=result,
            original_lines=original_lines,
            filtered_lines=len(kept),
            removed_tokens_estimate=base.removed_tokens_estimate + skipped,
        )