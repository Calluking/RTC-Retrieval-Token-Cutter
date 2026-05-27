"""Pytest / unittest log template folding.

Collapses long runs of *passing* per-test lines (the dominant volume in
SWE-bench test output) into a per-suite summary, while preserving:
  - The FAIL/ERROR result lines (so the agent still sees which test broke).
  - Failure detail blocks (the ====/---- delimited traceback regions).
  - The terminal summary lines (`Ran N tests`, `OK`, `FAILED (...)` or
    pytest's `=== N passed in T.Ts ===`).

Recognises two dialects:
  * unittest / django:  `test_name (mod.Class) ... ok`
                        optionally preceded by a docstring continuation line.
  * pytest:             `tests/file.py::test_name PASSED [pct%]`

If neither dialect matches the input, the text is returned unchanged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# unittest / django line:
#   test_name (mod.path.Class) ... ok|FAIL|ERROR|skipped 'reason'
_UT_LINE = re.compile(
    r"^(?P<head>test_\S+\s*(?:\([^)]+\))?(?:\n.*?)?)\s*\.\.\.\s*"
    r"(?P<outcome>ok|OK|FAIL|FAILED|ERROR|skipped(?:\s+'.*')?)\s*$"
)

# pytest line:
#   tests/file.py::test_name PASSED [50%]
_PT_LINE = re.compile(
    r"^(?P<path>\S+\.py)::(?P<test>[^\s]+)\s+"
    r"(?P<outcome>PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)"
    r"(?:\s+\[\s*\d+%\])?\s*$"
)

_BLOCK_DIVIDER = re.compile(r"^[=\-]{20,}$")
_PASSING = {"ok", "OK", "PASSED", "XPASS"}
_FAILING = {"FAIL", "FAILED", "ERROR", "XFAIL"}
_SKIPPED_PREFIX = "skipped"


@dataclass
class FoldResult:
    text: str
    original_chars: int
    shortened_chars: int
    passed_count: int
    failed_count: int
    skipped_count: int

    @property
    def shortening_ratio(self) -> float:
        if self.original_chars == 0:
            return 1.0
        return self.shortened_chars / self.original_chars


def _classify_unittest(line: str, prev: str | None) -> tuple[str, str] | None:
    """If `line` is a unittest result line, return (outcome, joined_head)."""
    m = _UT_LINE.match(line)
    if m:
        return m.group("outcome"), m.group("head")
    if prev is not None:
        joined = prev + "\n" + line
        m2 = _UT_LINE.match(joined)
        if m2:
            return m2.group("outcome"), m2.group("head")
    return None


def _classify_pytest(line: str) -> tuple[str, str] | None:
    m = _PT_LINE.match(line)
    if not m:
        return None
    return m.group("outcome"), f"{m.group('path')}::{m.group('test')}"


def _is_test_header_line(line: str) -> bool:
    """A `test_name (mod.Class)` line on its own (continuation form)."""
    s = line.strip()
    return bool(re.match(r"^test_\S+\s*\([^)]+\)\s*$", s))


def fold_test_output(text: str) -> FoldResult:
    """Fold long runs of passing test lines while preserving failure context."""
    original_chars = len(text)
    if not text:
        return FoldResult(text="", original_chars=0, shortened_chars=0,
                          passed_count=0, failed_count=0, skipped_count=0)

    lines = text.splitlines()
    n = len(lines)
    passed = 0
    failed = 0
    skipped = 0

    out: list[str] = []
    pending_pass_run = 0
    pending_pass_dialect: str | None = None

    def flush_pass_run() -> None:
        nonlocal pending_pass_run, pending_pass_dialect
        if pending_pass_run > 0:
            label = "passed" if pending_pass_dialect == "pt" else "ok"
            out.append(f"// ... {pending_pass_run} {label} test(s) folded ...")
            pending_pass_run = 0
            pending_pass_dialect = None

    i = 0
    while i < n:
        line = lines[i]

        pt = _classify_pytest(line)
        if pt is not None:
            outcome, _ = pt
            if outcome in _PASSING:
                pending_pass_run += 1
                pending_pass_dialect = "pt"
                passed += 1
                i += 1
                continue
            flush_pass_run()
            out.append(line)
            if outcome in _FAILING:
                failed += 1
            elif outcome == "SKIPPED":
                skipped += 1
            i += 1
            continue

        ut = _classify_unittest(line, prev=None)
        if ut is not None:
            outcome, _ = ut
            if outcome in _PASSING:
                pending_pass_run += 1
                pending_pass_dialect = "ut"
                passed += 1
                i += 1
                continue
            if outcome.startswith(_SKIPPED_PREFIX):
                flush_pass_run()
                out.append(line)
                skipped += 1
                i += 1
                continue
            flush_pass_run()
            out.append(line)
            failed += 1
            i += 1
            continue

        if (
            i + 1 < n
            and _is_test_header_line(line)
        ):
            m = _UT_LINE.match(line + "\n" + lines[i + 1])
            if m:
                outcome = m.group("outcome")
                if outcome in _PASSING:
                    pending_pass_run += 1
                    pending_pass_dialect = "ut"
                    passed += 1
                    i += 2
                    continue
                flush_pass_run()
                out.append(line)
                out.append(lines[i + 1])
                if outcome.startswith(_SKIPPED_PREFIX):
                    skipped += 1
                else:
                    failed += 1
                i += 2
                continue

        if (
            i + 1 < n
            and _is_test_header_line(line)
            and re.search(r"\.\.\.\s*(ok|OK|FAIL|FAILED|ERROR|skipped)", lines[i + 1])
        ):
            doc = lines[i + 1]
            m = re.search(r"\.\.\.\s*(ok|OK|FAIL|FAILED|ERROR|skipped)", doc)
            outcome = m.group(1)
            if outcome in _PASSING:
                pending_pass_run += 1
                pending_pass_dialect = "ut"
                passed += 1
                i += 2
                continue
            flush_pass_run()
            out.append(line)
            out.append(doc)
            if outcome.startswith(_SKIPPED_PREFIX):
                skipped += 1
            else:
                failed += 1
            i += 2
            continue

        flush_pass_run()
        out.append(line)
        i += 1

    flush_pass_run()

    if passed == 0 and failed == 0 and skipped == 0:
        return FoldResult(
            text=text,
            original_chars=original_chars,
            shortened_chars=original_chars,
            passed_count=0, failed_count=0, skipped_count=0,
        )

    folded = "\n".join(out)
    return FoldResult(
        text=folded,
        original_chars=original_chars,
        shortened_chars=len(folded),
        passed_count=passed,
        failed_count=failed,
        skipped_count=skipped,
    )