"""Python AST-based skeleton extraction.

Two extractors:

  * `extract_python_skeleton` — the primary, AST-driven path. Keeps module
    imports, type aliases, constants, and every class/function signature
    (with optional docstrings); drops function bodies; round-trips through
    ast.parse. Only works on *complete, parseable* Python modules.

  * `extract_python_slice_skeleton` — a regex-driven fallback for Python
    text that does NOT parse: file slices returned by Read with offset/limit,
    code fragments quoted in issue bodies, half-edited buffers. No AST,
    just line-by-line pattern keeping. Lossy by design but useful when the
    only alternative is shipping the slice verbatim.

The strategy layer (`filter/adapters/strategies/python_skeleton.py`) tries
the AST path first and falls back to the slice extractor on parse failure.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass


@dataclass
class SkeletonResult:
    """Result of a skeleton extraction pass."""
    text: str
    original_chars: int
    shortened_chars: int
    fallback_reason: str | None = None

    @property
    def shortening_ratio(self) -> float:
        if self.original_chars == 0:
            return 1.0
        return self.shortened_chars / self.original_chars


class _BodyDropper(ast.NodeTransformer):
    def __init__(self, keep_docstrings: bool):
        self.keep_docstrings = keep_docstrings

    def _replace_body(self, node: ast.AST) -> None:
        body = getattr(node, "body", None)
        if not body:
            return
        first = body[0]
        new_body: list[ast.stmt] = []
        if (
            self.keep_docstrings
            and isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            new_body.append(first)
        new_body.append(ast.Expr(value=ast.Constant(value=Ellipsis)))
        node.body = new_body

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._replace_body(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._replace_body(node)
        return node

    def visit_ClassDef(self, node: ast.ClassDef):
        node.body = [self.visit(stmt) for stmt in node.body]
        return node


def extract_python_skeleton(
    text: str,
    *,
    keep_docstrings: bool = True,
) -> SkeletonResult:
    """Extract a structural skeleton from Python source."""
    original_chars = len(text)
    if not text:
        return SkeletonResult(text="", original_chars=0, shortened_chars=0)

    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return SkeletonResult(
            text=text,
            original_chars=original_chars,
            shortened_chars=original_chars,
            fallback_reason=f"syntax_error: {exc.msg}",
        )

    if not keep_docstrings:
        if (
            tree.body
            and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)
        ):
            tree.body = tree.body[1:]

    _BodyDropper(keep_docstrings=keep_docstrings).visit(tree)
    ast.fix_missing_locations(tree)

    try:
        out = ast.unparse(tree)
    except Exception as exc:
        return SkeletonResult(
            text=text,
            original_chars=original_chars,
            shortened_chars=original_chars,
            fallback_reason=f"unparse_failed: {exc!r}",
        )

    return SkeletonResult(
        text=out,
        original_chars=original_chars,
        shortened_chars=len(out),
    )


_SIG_LINE = re.compile(
    r"^[ \t]*("
    r"@\S+"
    r"|async\s+def\s+\w"
    r"|def\s+\w"
    r"|class\s+\w"
    r"|from\s+\S+\s+import\b"
    r"|import\s+\w"
    r"|if\s+__name__\s*==\s*['\"]__main__['\"]"
    r")"
)

_CONST_LINE = re.compile(
    r"^[ \t]*[A-Z][A-Z0-9_]*\s*(?::\s*[^=]+)?\s*="
)


def extract_python_slice_skeleton(text: str) -> SkeletonResult:
    """Regex-based skeleton for Python text that doesn't parse as a module."""
    original_chars = len(text)
    if not text:
        return SkeletonResult(text="", original_chars=0, shortened_chars=0)

    out: list[str] = []
    body_run = 0
    for line in text.splitlines():
        is_sig = _SIG_LINE.match(line) is not None
        is_const = _CONST_LINE.match(line) is not None
        if is_sig or is_const:
            if body_run > 0:
                out.append(f"    # ... {body_run} body line(s) elided")
                body_run = 0
            out.append(line)
        else:
            body_run += 1
    if body_run > 0:
        out.append(f"    # ... {body_run} body line(s) elided")

    result = "\n".join(out)
    return SkeletonResult(
        text=result,
        original_chars=original_chars,
        shortened_chars=len(result),
    )