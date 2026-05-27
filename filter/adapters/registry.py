"""Registry: pick the best LibraryProfile for a given (command, output) pair."""

from __future__ import annotations

import shlex
from typing import Any

from filter.adapters.base import (
    AdapterMatch,
    LibraryProfile,
    SCORE_CATEGORY_HIT,
    SCORE_COMMAND_EXACT,
    SCORE_PATH_EXT_HIT,
    SCORE_PATTERN_HIT,
    SCORE_THRESHOLD,
    Strategy,
)


_STRATEGY_CACHE: dict[str, Strategy] | None = None


def _strategies() -> dict[str, Strategy]:
    """Lazy build the strategy_name → instance map."""
    global _STRATEGY_CACHE
    if _STRATEGY_CACHE is not None:
        return _STRATEGY_CACHE

    from filter.adapters.strategies.build_progress import BuildProgressStrategy
    from filter.adapters.strategies.diff_hunk import DiffHunkStrategy
    from filter.adapters.strategies.json_structure import JSONStructureStrategy
    from filter.adapters.strategies.lint_group import LintGroupStrategy
    from filter.adapters.strategies.match_group import MatchGroupStrategy
    from filter.adapters.strategies.pip_progress import PipProgressStrategy
    from filter.adapters.strategies.python_skeleton import PythonSkeletonStrategy
    from filter.adapters.strategies.repr_fold import ReprFoldStrategy
    from filter.adapters.strategies.request_log import RequestLogStrategy
    from filter.adapters.strategies.stats_extract import StatsExtractStrategy
    from filter.adapters.strategies.test_runner import TestRunnerStrategy
    from filter.adapters.strategies.tree_condense import TreeCondenseStrategy
    from filter.adapters.strategies.warning_group import WarningGroupStrategy

    _STRATEGY_CACHE = {s.name: s for s in [
        BuildProgressStrategy(),
        DiffHunkStrategy(),
        JSONStructureStrategy(),
        LintGroupStrategy(),
        MatchGroupStrategy(),
        PipProgressStrategy(),
        PythonSkeletonStrategy(),
        ReprFoldStrategy(),
        RequestLogStrategy(),
        StatsExtractStrategy(),
        TestRunnerStrategy(),
        TreeCondenseStrategy(),
        WarningGroupStrategy(),
    ]}
    return _STRATEGY_CACHE


def _first_token(command: str | None) -> str | None:
    """Return the first token of a Bash command line, or None."""
    if not command:
        return None
    try:
        parts = shlex.split(command, comments=False, posix=True)
    except ValueError:
        parts = command.split()
    if not parts:
        return None
    head = parts[0]
    i = 0
    while i < len(parts) and "=" in parts[i] and not parts[i].startswith("-"):
        i += 1
    if i >= len(parts):
        return head
    return parts[i]


def _path_ext(path: str | None) -> str | None:
    if not path:
        return None
    if "." not in path:
        return None
    return "." + path.rsplit(".", 1)[-1].lower()


def _score(
    profile: LibraryProfile,
    *,
    first_token: str | None,
    text: str,
    path_ext: str | None,
    category: str | None,
) -> tuple[int, tuple[str, ...]]:
    score = 0
    reasons: list[str] = []

    if first_token and profile.command_hints:
        if first_token in profile.command_hints:
            score += SCORE_COMMAND_EXACT
            reasons.append(f"cmd={first_token}")

    if category and profile.category_hints and category in profile.category_hints:
        score += SCORE_CATEGORY_HIT
        reasons.append(f"category={category}")

    if profile.detect_patterns and text:
        for pat in profile.detect_patterns:
            if pat.search(text):
                score += SCORE_PATTERN_HIT
                reasons.append(f"pattern={pat.pattern[:30]}")
                break

    if path_ext and profile.path_hints and path_ext in profile.path_hints:
        score += SCORE_PATH_EXT_HIT
        reasons.append(f"path={path_ext}")

    return score, tuple(reasons)


def route(
    text: str,
    *,
    command: str | None = None,
    tool_name: str | None = None,
    path: str | None = None,
    category: str | None = None,
    only: str | None = None,
) -> AdapterMatch:
    """Pick the best-matching profile for this call."""
    from filter.adapters.profiles import PROFILES

    strategies = _strategies()
    first_token = _first_token(command)
    path_ext = _path_ext(path)

    if only:
        for p in PROFILES:
            if p.name == only:
                return AdapterMatch(
                    profile=p,
                    score=SCORE_COMMAND_EXACT,
                    strategy=strategies.get(p.strategy_name),
                    reasons=("forced",),
                )
        return AdapterMatch(profile=None, score=0, strategy=None,
                            reasons=("forced_not_found",))

    best: tuple[int, LibraryProfile, tuple[str, ...]] | None = None
    for p in PROFILES:
        score, reasons = _score(
            p, first_token=first_token, text=text,
            path_ext=path_ext, category=category,
        )
        if score <= 0:
            continue
        if best is None or (score, p.priority) > (best[0], best[1].priority):
            best = (score, p, reasons)

    if best is None or best[0] < SCORE_THRESHOLD:
        return AdapterMatch(profile=None, score=0, strategy=None)

    score, profile, reasons = best
    strategy = strategies.get(profile.strategy_name)
    return AdapterMatch(
        profile=profile,
        score=score,
        strategy=strategy,
        reasons=reasons,
    )