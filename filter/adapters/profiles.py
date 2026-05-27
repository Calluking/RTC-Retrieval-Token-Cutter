"""Library + command profiles for the Filter adapter registry."""

from __future__ import annotations

import re

from filter.adapters.base import LibraryProfile


RE_PYTEST_OUT = re.compile(r"::\w+ (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)")
RE_PYTEST_SUMMARY = re.compile(r"={3,}\s*\d+ (passed|failed|error|skipped)", re.I)
RE_UNITTEST_RAN = re.compile(r"^Ran \d+ tests? in \d", re.M)


PROFILES: list[LibraryProfile] = [
    LibraryProfile(
        name="python_source",
        strategy_name="python_skeleton",
        path_hints=(".py",),
        category_hints=("skill",),
        detect_patterns=(
            re.compile(r"^(import \S|from \S+ import )", re.M),
            re.compile(r"^(async\s+)?(def |class )\w", re.M),
        ),
        config={"keep_docstrings": True},
        priority=58,
    ),
    LibraryProfile(
        name="django",
        strategy_name="test_runner",
        detect_patterns=(
            RE_UNITTEST_RAN,
            re.compile(r"Creating test database for alias", re.M),
            re.compile(r"^Testing against Django installed", re.M),
            re.compile(r"^Synchronizing apps without migrations", re.M),
        ),
        config={
            "noise_lines": [
                r"^Synchronizing apps without migrations",
                r"^Operations to perform",
                r"^Apply all migrations",
                r"^\s+Apply all migrations",
                r"^\s+Synchronize unmigrated apps",
                r"^Importing application ",
                r"^Skipping setup of unused database",
                r"^Destroying test database",
                r"^\+ source /opt/miniconda3/bin/activate",
                r"^\+\+ ",
                r"^\+\+\+ ",
            ],
        },
        priority=70,
    ),
    LibraryProfile(
        name="pytest",
        strategy_name="test_runner",
        command_hints=("pytest", "py.test"),
        detect_patterns=(RE_PYTEST_OUT, RE_PYTEST_SUMMARY),
        config={
            "noise_lines": [
                r"^plugins: ",
                r"^collecting \.\.\.",
                r"^cachedir:",
                r"^rootdir:",
                r"^platform ",
            ],
        },
        priority=70,
    ),
    LibraryProfile(
        name="playwright",
        strategy_name="test_runner",
        command_hints=("playwright",),
        detect_patterns=(re.compile(r"Running \d+ tests using \d+ workers"),),
        config={},
        priority=60,
    ),
    LibraryProfile(
        name="vitest",
        strategy_name="test_runner",
        command_hints=("vitest",),
        detect_patterns=(re.compile(r"^\s*Test Files\s+\d+ passed", re.M),),
        config={},
        priority=60,
    ),
    LibraryProfile(
        name="sphinx",
        strategy_name="build_progress",
        command_hints=("sphinx-build",),
        detect_patterns=(re.compile(r"^building \[(html|man|epub)\]", re.M),),
        config={
            "drop_patterns": [
                r"^reading sources",
                r"^writing output",
                r"^copying images",
                r"^copying static files",
                r"^copying extra files",
                r"^\[\d+/\d+\]",
                r"^updating environment",
                r"^pickling environment",
                r"^checking consistency",
                r"^looking for now-outdated files",
                r"^preparing documents",
                r"^dumping",
            ],
        },
        priority=55,
    ),
    LibraryProfile(
        name="next",
        strategy_name="build_progress",
        command_hints=("next",),
        detect_patterns=(re.compile(r"Compiled successfully|Compiling|Skipping|Linting"),),
        config={
            "drop_patterns": [r"^- info ", r"^✓ Compiling", r"^Wait, compiling"],
        },
        priority=55,
    ),
    LibraryProfile(
        name="prisma",
        strategy_name="build_progress",
        command_hints=("prisma",),
        detect_patterns=(re.compile(r"^Prisma schema loaded"),),
        config={"drop_patterns": [r"^Generating ", r"^Generated ", r"^\d+ms"]},
        priority=55,
    ),
    LibraryProfile(
        name="pnpm",
        strategy_name="build_progress",
        command_hints=("pnpm",),
        detect_patterns=(re.compile(r"^Progress:|^Packages:|^Resolving:"),),
        config={
            "drop_patterns": [
                r"^Progress:", r"^Packages: ", r"^Resolving: ",
                r"^Downloading registry", r"^Building fresh packages",
            ],
        },
        priority=55,
    ),
    LibraryProfile(
        name="astropy",
        strategy_name="warning_group",
        detect_patterns=(
            re.compile(r"\bAstropyDeprecationWarning\b"),
            re.compile(r"\bAstropyUserWarning\b"),
        ),
        config={"warning_classes": [
            r"\bAstropyDeprecationWarning\b",
            r"\bAstropyUserWarning\b",
            r"\bAstropyWarning\b",
        ]},
        priority=55,
    ),
    LibraryProfile(
        name="sklearn",
        strategy_name="warning_group",
        detect_patterns=(
            re.compile(r"\bConvergenceWarning\b"),
            re.compile(r"sklearn\."),
        ),
        config={"warning_classes": [
            r"\bConvergenceWarning\b",
            r"\bFutureWarning\b",
            r"\bDataConversionWarning\b",
        ]},
        priority=55,
    ),
    LibraryProfile(
        name="flask",
        strategy_name="request_log",
        detect_patterns=(
            re.compile(r"Werkzeug"),
            re.compile(r"^ \* (Running on|Restarting with|Debugger PIN)", re.M),
        ),
        config={},
        priority=55,
    ),
    LibraryProfile(
        name="requests",
        strategy_name="request_log",
        detect_patterns=(
            re.compile(r"requests\.exceptions\."),
            re.compile(r"urllib3\.connectionpool"),
        ),
        config={},
        priority=50,
    ),
    LibraryProfile(
        name="xarray",
        strategy_name="repr_fold",
        detect_patterns=(re.compile(r"<xarray\.(Dataset|DataArray)>"),),
        config={
            "repr_starts": [r"<xarray\.(Dataset|DataArray)>"],
            "repr_ends": [r"^Attributes:|^$"],
            "threshold_lines": 12,
        },
        priority=55,
    ),
    LibraryProfile(
        name="matplotlib",
        strategy_name="repr_fold",
        detect_patterns=(
            re.compile(r"<Figure size \d"),
            re.compile(r"matplotlib\.figure\.Figure"),
        ),
        config={
            "repr_starts": [r"<Figure size", r"Figure\(", r"Axes\("],
            "threshold_lines": 8,
        },
        priority=50,
    ),
    LibraryProfile(
        name="sympy",
        strategy_name="repr_fold",
        detect_patterns=(
            re.compile(r"\bsympy\."),
            re.compile(r"\\begin\{(matrix|equation|align)\}"),
        ),
        config={
            "repr_starts": [r"Matrix\(\[", r"\\begin\{(matrix|equation|align)\}"],
            "repr_ends": [r"\]\)$", r"\\end\{(matrix|equation|align)\}"],
            "threshold_lines": 15,
        },
        priority=50,
    ),
    LibraryProfile(
        name="pylint",
        strategy_name="lint_group",
        command_hints=("pylint",),
        detect_patterns=(re.compile(r":\d+:\d+:\s+[CRWE]\d{4}:"),),
        config={
            "line_pattern": r"^(?P<path>[^:]+):(?P<line>\d+):(?P<col>\d+):\s+(?P<code>[CRWEF]\d{4}):",
            "passthrough_patterns": [r"^Your code has been rated"],
        },
        priority=60,
    ),
    LibraryProfile(
        name="ruff",
        strategy_name="lint_group",
        command_hints=("ruff",),
        detect_patterns=(re.compile(r":\d+:\d+:\s+[A-Z]\d{2,4}\b"),),
        config={
            "line_pattern": r"^(?P<path>[^:]+):(?P<line>\d+):(?P<col>\d+):\s+(?P<code>[A-Z]\d{2,4})",
            "passthrough_patterns": [r"^Found \d+ error", r"^All checks passed"],
        },
        priority=60,
    ),
    LibraryProfile(
        name="mypy",
        strategy_name="lint_group",
        command_hints=("mypy",),
        detect_patterns=(re.compile(r":\s+(error|note|warning):\s"),),
        config={
            "line_pattern": r"^(?P<path>[^:]+):(?P<line>\d+):\s+(?P<code>error|note|warning):",
            "passthrough_patterns": [r"^Found \d+ error", r"^Success: "],
        },
        priority=60,
    ),
    LibraryProfile(
        name="tsc",
        strategy_name="lint_group",
        command_hints=("tsc",),
        detect_patterns=(re.compile(r"\.ts\(\d+,\d+\):\s+error\s+TS\d+"),),
        config={
            "line_pattern": r"^(?P<path>[^:(]+)\((?P<line>\d+),(?P<col>\d+)\):\s+error\s+(?P<code>TS\d+)",
            "passthrough_patterns": [r"^Found \d+ error"],
        },
        priority=60,
    ),
    LibraryProfile(
        name="eslint",
        strategy_name="lint_group",
        command_hints=("eslint",),
        detect_patterns=(re.compile(r"^\s+\d+:\d+\s+(error|warning)\s+"),),
        config={
            "line_pattern": r"^\s+(?P<line>\d+):(?P<col>\d+)\s+(?P<code>error|warning)\s+(?P<msg>.+?)\s+(?P<rule>\S+)$",
        },
        priority=60,
    ),
    LibraryProfile(
        name="prettier",
        strategy_name="lint_group",
        command_hints=("prettier",),
        detect_patterns=(re.compile(r"^\[(warn|error)\]"),),
        config={"line_pattern": r"^\[(?P<code>warn|error)\]\s+(?P<path>.+)"},
        priority=55,
    ),
    LibraryProfile(
        name="git_status",
        strategy_name="stats_extract",
        command_hints=("git",),
        detect_patterns=(
            re.compile(r"^On branch ", re.M),
            re.compile(r"^Changes to be committed:", re.M),
            re.compile(r"^Untracked files:", re.M),
            re.compile(r"^Changes not staged for commit:", re.M),
        ),
        config={
            "sections": [
                (r"^Changes to be committed:", 10),
                (r"^Changes not staged for commit:", 10),
                (r"^Untracked files:", 5),
            ],
        },
        priority=65,
    ),
    LibraryProfile(
        name="git_diff",
        strategy_name="diff_hunk",
        command_hints=(),
        detect_patterns=(
            re.compile(r"^diff --git a/", re.M),
            re.compile(r"^@@\s+-\d+(,\d+)?\s+\+\d+(,\d+)?\s+@@", re.M),
        ),
        config={"context_window": 3},
        priority=65,
    ),
    LibraryProfile(
        name="git_log",
        strategy_name="build_progress",
        command_hints=(),
        detect_patterns=(re.compile(r"^commit [0-9a-f]{7,40}$", re.M),),
        config={"keep_patterns": [r"^commit ", r"^Author:", r"^Date:", r"^\s{4}"]},
        priority=55,
    ),
    LibraryProfile(
        name="gh",
        strategy_name="json_structure",
        command_hints=("gh",),
        path_hints=(".json",),
        config={"max_depth": 4, "max_array_examples": 3},
        priority=55,
    ),
    LibraryProfile(
        name="gt",
        strategy_name="tree_condense",
        command_hints=("gt",),
        config={"threshold": 15, "sample_per_ext": 5},
        priority=55,
    ),
    LibraryProfile(
        name="ls",
        strategy_name="tree_condense",
        command_hints=("ls",),
        config={"threshold": 40, "sample_per_ext": 5},
        priority=60,
    ),
    LibraryProfile(
        name="tree",
        strategy_name="tree_condense",
        command_hints=("tree",),
        config={"threshold": 30, "sample_per_ext": 5},
        priority=60,
    ),
    LibraryProfile(
        name="find",
        strategy_name="tree_condense",
        command_hints=("find", "fd"),
        config={"threshold": 30, "sample_per_ext": 5},
        priority=60,
    ),
    LibraryProfile(
        name="deps",
        strategy_name="tree_condense",
        command_hints=("npm", "yarn"),
        detect_patterns=(re.compile(r"^[├└│─]+ "),),
        config={"threshold": 30, "sample_per_ext": 5},
        priority=45,
    ),
    LibraryProfile(
        name="grep",
        strategy_name="match_group",
        command_hints=("grep", "egrep", "fgrep"),
        detect_patterns=(re.compile(r"^[^:\s][^:]*:\d+:"),),
        config={"sample_per_file": 5},
        priority=60,
    ),
    LibraryProfile(
        name="rg",
        strategy_name="match_group",
        command_hints=("rg", "ripgrep"),
        detect_patterns=(re.compile(r"^[^:\s][^:]*:\d+:"),),
        config={"sample_per_file": 5},
        priority=60,
    ),
    LibraryProfile(
        name="json",
        strategy_name="json_structure",
        command_hints=("jq",),
        path_hints=(".json",),
        config={"max_depth": 4, "max_array_examples": 2, "max_total_chars": 4000},
        priority=55,
    ),
    LibraryProfile(
        name="env",
        strategy_name="stats_extract",
        command_hints=("env", "printenv"),
        config={
            "sections": [
                (r"^[A-Z][A-Z0-9_]+=", 10),
            ],
            "default_sample": 10,
        },
        priority=50,
    ),
    LibraryProfile(
        name="pip",
        strategy_name="pip_progress",
        command_hints=("pip", "pip3"),
        detect_patterns=(re.compile(r"^Requirement already satisfied:"),),
        config={},
        priority=60,
    ),
]