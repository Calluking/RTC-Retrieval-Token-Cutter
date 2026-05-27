"""SWE-bench Lite task-type detection and property extraction for natural-language memory.

Detects the downstream task type from a SWE-bench Lite problem statement
and extracts structured properties for L1MemoryPolicy storage.

Task types:
  - code_debug      : bug/issue reproduction and fix
  - code_write      : new feature or implementation
  - refactor        : code restructuring without behavior change
  - explain         : investigation, analysis, or clarification
  - test            : test writing or modification
  - patch_review    : reviewing an existing patch/diff

Properties extracted per task type mirror the Filter priority system:
  - Priority 0: critical (error_type, stack trace, file paths)
  - Priority 1: high (function names, test targets, steps)
  - Priority 2: medium (description body, expected behavior)
  - Priority 3: low (version info, meta)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# Task-type labels used as L1 routing_key prefixes
TASK_TYPE_LABELS = {
    "code_debug": "code_debug",
    "code_write": "code_write",
    "refactor": "refactor",
    "explain": "explain",
    "test": "test",
    "patch_review": "patch_review",
}


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Error/traceback signals — suggests code_debug
_ERROR_RE = re.compile(
    r"(Traceback|Error:|Exception:|failed|failed with|"
    r"crashed|timeout|segfault|Segmentation|AssertionError|"
    r"raise \w+Error|panic:)",
    re.IGNORECASE,
)

# Bug report framing — suggests code_debug
_BUG_RE = re.compile(
    r"(bug|issue|wrong|incorrect|broken|fails?|doesn't work|"
    r"does not work|not working|unexpected|memory leak|"
    r"regression|infinite loop|deadlock|race condition)",
    re.IGNORECASE,
)

# New feature / enhancement framing — suggests code_write
_FEATURE_RE = re.compile(
    r"(add|implement|support|introduce|extend|enhance|"
    r"new feature|should allow|should support|ability to|"
    r"allow users to|provide a way to|enables?|provides?)",
    re.IGNORECASE,
)

# Refactor framing — suggests refactor
_REFACTOR_RE = re.compile(
    r"(refactor|restructure|redo|rewrite|clean up|"
    r"simplify|deprecate|remove redundant|extract method|"
    r"move code|separate concerns|technical debt)",
    re.IGNORECASE,
)

# Test writing — suggests test
_TEST_RE = re.compile(
    r"(test|coverage|write a test|add test|test case|"
    r"unit test|integration test|benchmark|"
    r"reproduce the issue|verify|validation)",
    re.IGNORECASE,
)

# Explanation/investigation — suggests explain
_EXPLAIN_RE = re.compile(
    r"(investigate|explain|understand|clarify|determine|"
    r"find out|why is|how does|what is the|analyze|"
    r"document|comment|readme|changelog|release note)",
    re.IGNORECASE,
)

# Patch/diff review — suggests patch_review
_PATCH_RE = re.compile(
    r"(patch|diff|changeset|review|check this|"
    r"see (the )?following (changes?|patch)|"
    r"apply (the )?fix|proposed fix|proposed change)",
    re.IGNORECASE,
)

# File path extraction
_FILE_PATH_RE = re.compile(
    r"['\"](/[a-zA-Z0-9_./\\-]+\.[a-zA-Z]{1,10})['\"]|"
    r"(\b[a-zA-Z0-9_./\\-]+\.[a-zA-Z]{1,10})(?=[:\s]|$)",
)

# Function/method name extraction — must be preceded by keyword on same line
_FUNC_RE = re.compile(
    r"(?:^|\n)(?:def|async def|class|function|method)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
)

# Test target extraction (e.g., "test_foo.py", "TestClass", "test_function")
_TEST_TARGET_RE = re.compile(
    r"(test_[a-zA-Z0-9_]+\.py|"
    r"[a-zA-Z]+Test(?:Case)?|"
    r"def test_[a-zA-Z0-9_]+|"
    r"(?:run|execute|call)\s+[`'\"]([a-zA-Z0-9_]+)[`'\"]{0,3})",
)

# Error type extraction (e.g., "ValueError", "TypeError", "KeyError")
_ERROR_TYPE_RE = re.compile(
    r"([A-Z][a-zA-Z]+Error|"
    r"[A-Z][a-zA-Z]+Exception|"
    r"(?:Error|Exception|Type):\s*([A-Z][a-zA-Z]+))",
)

# Version info
_VERSION_RE = re.compile(
    r"(version|v?\d+\.\d+(?:\.\d+)?|"
    r"[a-zA-Z0-9_.-]+@[a-f0-9]{7,})",
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TaskTypeResult:
    task_type: str
    confidence: float  # 0.0–1.0
    properties: dict = field(default_factory=dict)
    routing_key: str = ""


@dataclass
class SWEInstanceFields:
    """Structured fields extracted from a SWE-bench Lite instance."""
    instance_id: str
    repo: str
    base_commit: str
    problem_statement: str
    hints_text: str = ""


# ---------------------------------------------------------------------------
# Core classifier
# ---------------------------------------------------------------------------

def detect_task_type(problem: str) -> tuple[str, float]:
    """Detect the primary task type from a SWE-bench problem statement.

    Returns:
        (task_type, confidence) — confidence in [0.0, 1.0]
    """
    if not problem:
        return "explain", 0.3

    # Score each type by pattern matches
    scores: dict[str, float] = {
        "code_debug": 0.0,
        "code_write": 0.0,
        "refactor": 0.0,
        "explain": 0.0,
        "test": 0.0,
        "patch_review": 0.0,
    }

    # Strong signals first (bounce early)
    if _ERROR_RE.search(problem):
        scores["code_debug"] += 0.5
    if _BUG_RE.search(problem):
        scores["code_debug"] += 0.3
    if _TEST_RE.search(problem):
        scores["test"] += 0.3

    # Medium signals
    if _FEATURE_RE.search(problem):
        scores["code_write"] += 0.35
    if _REFACTOR_RE.search(problem):
        scores["refactor"] += 0.4
    if _EXPLAIN_RE.search(problem):
        scores["explain"] += 0.3
    if _PATCH_RE.search(problem):
        scores["patch_review"] += 0.4

    # Context clues: short problem statements tend to be bugs
    if len(problem) < 300:
        if scores["code_debug"] == 0 and scores["code_write"] == 0:
            scores["code_debug"] += 0.25

    # Normalize: highest score wins; confidence = how dominant vs. second place
    sorted_scores = sorted(scores.values(), reverse=True)
    top = sorted_scores[0]
    second = sorted_scores[1] if len(sorted_scores) > 1 else 0.0

    # confidence = margin over second-place; min 0.4 if any signal found
    if top > 0:
        confidence = max(0.4, min(1.0, (top - second + 0.1) / (top + 0.1)))
    else:
        return "explain", 0.2

    type_map = {v: k for k, v in TASK_TYPE_LABELS.items()}
    best_type = max(scores, key=scores.get)  # type: ignore

    return best_type, round(confidence, 2)


# ---------------------------------------------------------------------------
# Property extractors (per task type)
# ---------------------------------------------------------------------------

def extract_properties(
    fields: SWEInstanceFields,
    task_type: str,
) -> dict:
    """Extract structured properties from a SWE-bench Lite instance.

    Properties are keyed for L1MemoryPolicy content_append/overview_append
    storage. Values are kept short (truncated) to avoid storage explosion.
    """
    problem = fields.problem_statement
    hints = fields.hints_text
    props: dict[str, str] = {}

    # Always record instance metadata (priority 3)
    props["instance_id"] = fields.instance_id
    props["repo"] = fields.repo
    if fields.base_commit:
        props["base_commit"] = fields.base_commit[:12]  # short hash

    # Task-specific extraction
    if task_type == "code_debug":
        _extract_debug_properties(problem, hints, props)
    elif task_type == "code_write":
        _extract_write_properties(problem, hints, props)
    elif task_type == "refactor":
        _extract_refactor_properties(problem, hints, props)
    elif task_type == "test":
        _extract_test_properties(problem, hints, props)
    elif task_type == "patch_review":
        _extract_patch_properties(problem, hints, props)
    else:
        _extract_explain_properties(problem, hints, props)

    return props


def _extract_debug_properties(problem: str, hints: str, props: dict) -> None:
    """Extract properties for code_debug task type (priority order 0→3)."""
    # Priority 0: error type + stack trace hints
    err_matches = _ERROR_TYPE_RE.findall(problem)
    if err_matches:
        flat = [m[0] if isinstance(m, tuple) else m for m in err_matches]
        unique_errs = list(dict.fromkeys(flat))[:5]
        props["error_types"] = ", ".join(unique_errs)

    # Error description in first non-header line
    first_meaningful = ""
    for line in problem.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            first_meaningful = stripped
            break
    if first_meaningful and len(first_meaningful) > 10:
        props["error_summary"] = first_meaningful[:120]

    # Priority 1: file paths and function names
    file_paths = _FILE_PATH_RE.findall(problem)
    if file_paths:
        flat_paths = [p if isinstance(p, str) else p[0] for p in file_paths]
        unique_paths = [x for x in dict.fromkeys(flat_paths) if x][:8]
        props["file_paths"] = ", ".join(unique_paths)

    funcs = _FUNC_RE.findall(problem)
    if funcs:
        props["functions_mentioned"] = ", ".join(dict.fromkeys(funcs))[:100]

    # Priority 2: expected vs actual behavior
    expected = _extract_section(problem, ["expected", "expect", "should"])
    if expected:
        props["expected_behavior"] = expected[:200]

    actual = _extract_section(problem, ["actual", "observed", "instead"])
    if actual:
        props["actual_behavior"] = actual[:200]

    # Priority 3: version / environment
    if hints:
        props["hints_text"] = hints[:300]


def _extract_write_properties(problem: str, hints: str, props: dict) -> None:
    """Extract properties for code_write task type."""
    # Priority 0: what to add/implement (first non-header line = feature summary)
    first_meaningful = ""
    for line in problem.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            first_meaningful = stripped
            break
    if first_meaningful and len(first_meaningful) > 10:
        props["feature_summary"] = first_meaningful[:120]

    # Priority 1: file paths and function signatures
    file_paths = _FILE_PATH_RE.findall(problem)
    if file_paths:
        flat_paths = [p if isinstance(p, str) else p[0] for p in file_paths]
        unique_paths = [x for x in dict.fromkeys(flat_paths) if x][:8]
        props["target_files"] = ", ".join(unique_paths)

    funcs = _FUNC_RE.findall(problem)
    if funcs:
        props["functions_mentioned"] = ", ".join(dict.fromkeys(funcs))[:100]

    # Priority 2: description with acceptance criteria
    body = _strip_headers(problem)
    if body:
        props["description"] = body[:300]

    if hints:
        props["hints_text"] = hints[:200]


def _extract_refactor_properties(problem: str, hints: str, props: dict) -> None:
    """Extract properties for refactor task type."""
    # Priority 0: what to refactor
    first_meaningful = ""
    for line in problem.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            first_meaningful = stripped
            break
    if first_meaningful:
        props["refactor_summary"] = first_meaningful[:120]

    file_paths = _FILE_PATH_RE.findall(problem)
    if file_paths:
        flat_paths = [p if isinstance(p, str) else p[0] for p in file_paths]
        unique_paths = [x for x in dict.fromkeys(flat_paths) if x][:8]
        props["target_files"] = ", ".join(unique_paths)

    funcs = _FUNC_RE.findall(problem)
    if funcs:
        props["functions_mentioned"] = ", ".join(dict.fromkeys(funcs))[:100]

    if hints:
        props["hints_text"] = hints[:200]


def _extract_test_properties(problem: str, hints: str, props: dict) -> None:
    """Extract properties for test task type."""
    # Priority 0: what to test and how
    first_meaningful = ""
    for line in problem.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            first_meaningful = stripped
            break
    if first_meaningful:
        props["test_summary"] = first_meaningful[:120]

    # Test targets (test file names, class names)
    test_targets = _TEST_TARGET_RE.findall(problem)
    if test_targets:
        flat = [t if isinstance(t, str) else t for t in test_targets]
        unique = list(dict.fromkeys(flat))[:10]
        props["test_targets"] = ", ".join(unique)

    # Which functionality to test (file paths)
    file_paths = _FILE_PATH_RE.findall(problem)
    if file_paths:
        flat_paths = [p if isinstance(p, str) else p[0] for p in file_paths]
        unique_paths = [x for x in dict.fromkeys(flat_paths) if x][:8]
        props["files_to_test"] = ", ".join(unique_paths)

    if hints:
        props["hints_text"] = hints[:200]


def _extract_patch_properties(problem: str, hints: str, props: dict) -> None:
    """Extract properties for patch_review task type."""
    first_meaningful = ""
    for line in problem.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            first_meaningful = stripped
            break
    if first_meaningful:
        props["patch_summary"] = first_meaningful[:120]

    # Extract diff-like content indicators
    if "diff" in problem.lower() or "---" in problem or "+" in problem[:200]:
        props["contains_diff"] = "yes"

    file_paths = _FILE_PATH_RE.findall(problem)
    if file_paths:
        flat_paths = [p if isinstance(p, str) else p[0] for p in file_paths]
        unique_paths = [x for x in dict.fromkeys(flat_paths) if x][:8]
        props["patched_files"] = ", ".join(unique_paths)

    if hints:
        props["hints_text"] = hints[:200]


def _extract_explain_properties(problem: str, hints: str, props: dict) -> None:
    """Extract properties for explain task type."""
    first_meaningful = ""
    for line in problem.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            first_meaningful = stripped
            break
    if first_meaningful:
        props["question_summary"] = first_meaningful[:120]

    file_paths = _FILE_PATH_RE.findall(problem)
    if file_paths:
        flat_paths = [p if isinstance(p, str) else p[0] for p in file_paths]
        unique_paths = [x for x in dict.fromkeys(flat_paths) if x][:8]
        props["files_in_scope"] = ", ".join(unique_paths)

    funcs = _FUNC_RE.findall(problem)
    if funcs:
        props["functions_mentioned"] = ", ".join(dict.fromkeys(funcs))[:100]

    if hints:
        props["hints_text"] = hints[:200]


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

_HEADER_RE = re.compile(r"^#{1,4}\s+\S", re.MULTILINE)


def _strip_headers(text: str) -> str:
    """Strip markdown headers, return body text."""
    lines = text.splitlines()
    body_lines = [l for l in lines if not _HEADER_RE.match(l.strip())]
    return "\n".join(body_lines).strip()


_SECTION_HEADERS = {
    "expected": re.compile(r"(?:^|\n)#{1,4}\s*(?:expected|expect|expected behavior)", re.IGNORECASE),
    "actual": re.compile(r"(?:^|\n)#{1,4}\s*(?:actual|observed|actual behavior)", re.IGNORECASE),
}


def _extract_section(text: str, keywords: list[str]) -> str:
    """Extract first paragraph following a section header matching keywords."""
    lines = text.splitlines()
    capturing = False
    capture: list[str] = []
    for line in lines:
        stripped = line.strip()
        if any(re.search(rf"(?:^|\n)#{1,4}\s*{kw}", text, re.IGNORECASE) for kw in keywords):
            capturing = True
            continue
        if capturing:
            if _HEADER_RE.match(stripped):
                break
            if stripped:
                capture.append(stripped)
            elif capture:
                # Empty line after content — stop
                break
    return " ".join(capture) if capture else ""


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def extract_swebench_lite_properties(
    instance_id: str,
    repo: str,
    base_commit: str,
    problem_statement: str,
    hints_text: str = "",
) -> TaskTypeResult:
    """Classify a SWE-bench Lite instance and extract natural-language memory properties.

    This is the primary entry point for L1MemoryPolicy task-aware extraction.

    Args:
        instance_id: SWE-bench Lite instance ID (e.g., "pallets__flask-4045")
        repo: GitHub repository (e.g., "pallets/flask")
        base_commit: Base commit SHA
        problem_statement: The issue / problem statement text
        hints_text: Optional hints text from the instance

    Returns:
        TaskTypeResult with task_type, confidence, routing_key, and properties dict
    """
    fields = SWEInstanceFields(
        instance_id=instance_id,
        repo=repo,
        base_commit=base_commit,
        problem_statement=problem_statement,
        hints_text=hints_text,
    )

    task_type, confidence = detect_task_type(problem_statement)
    properties = extract_properties(fields, task_type)

    # Build routing_key: "swebench_lite/{task_type}/{short_instance_id}"
    short_id = instance_id.replace("/", "__", 1).replace("__", "_", 1)
    routing_key = f"swebench_lite/{task_type}/{short_id}"

    return TaskTypeResult(
        task_type=task_type,
        confidence=confidence,
        properties=properties,
        routing_key=routing_key,
    )


def routing_key_for_instance(instance_id: str, task_type: str) -> str:
    """Build a stable routing_key for a SWE-bench Lite instance.

    Use this to pre-compute routing_key without full property extraction.
    """
    short_id = instance_id.replace("/", "__", 1).replace("__", "_", 1)
    return f"swebench_lite/{task_type}/{short_id}"
