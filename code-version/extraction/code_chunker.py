"""AST-first code chunking utilities for code memory ingestion."""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from typing import Any


@dataclass
class CodeChunk:
    """A deterministic code chunk derived from a source file."""

    language: str
    file_path: str
    symbol: str
    start_line: int
    end_line: int
    content: str
    chunk_hash: str
    signature: str = ""
    symbol_kind: str | None = None
    metadata: dict[str, Any] | None = None

    @property
    def routing_key(self) -> str:
        return f"{self.language}:{self.file_path}:{self.symbol}:{self.start_line}-{self.end_line}"


def detect_language(file_path: str, hint: str | None = None) -> str:
    """Infer language from hint or file extension."""
    if hint:
        return hint.lower().strip()

    lower = file_path.lower()
    if lower.endswith(".py"):
        return "python"
    if lower.endswith(".ts"):
        return "typescript"
    if lower.endswith(".tsx"):
        return "tsx"
    if lower.endswith(".js"):
        return "javascript"
    if lower.endswith(".jsx"):
        return "jsx"
    if lower.endswith(".go"):
        return "go"
    if lower.endswith(".rs"):
        return "rust"
    if lower.endswith(".java"):
        return "java"
    if lower.endswith(".cpp") or lower.endswith(".cc") or lower.endswith(".cxx"):
        return "cpp"
    if lower.endswith(".c"):
        return "c"
    return "unknown"


def chunk_source_code(
    source: str,
    file_path: str,
    *,
    language: str | None = None,
    target_chars: int = 2500,
    overlap_chars: int = 300,
    max_chars: int = 4000,
) -> list[CodeChunk]:
    """Chunk source code with AST-first strategy and line-window fallback."""
    lang = detect_language(file_path, language)
    if lang == "python":
        chunks = _chunk_python_ast(source, file_path, lang, max_chars=max_chars)
        if chunks:
            return chunks
    return _chunk_line_windows(
        source,
        file_path,
        lang,
        target_chars=target_chars,
        overlap_chars=overlap_chars,
        max_chars=max_chars,
        symbol_kind="code",
    )


def _chunk_python_ast(
    source: str,
    file_path: str,
    language: str,
    *,
    max_chars: int,
) -> list[CodeChunk]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.splitlines()
    file_imports = _extract_python_imports(tree)
    chunks: list[CodeChunk] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        start = getattr(node, "lineno", 1)
        end = getattr(node, "end_lineno", start)
        if start < 1 or end < start:
            continue

        symbol = getattr(node, "name", f"symbol_{len(chunks) + 1}")
        if isinstance(node, ast.AsyncFunctionDef):
            symbol_kind = "async_function"
        elif isinstance(node, ast.FunctionDef):
            symbol_kind = "function"
        else:
            symbol_kind = "type"
        signature = _build_python_signature(node)
        graph_metadata = _build_python_graph_metadata(node, file_imports)
        content = _slice_lines(lines, start, end)
        if not content.strip():
            continue

        if len(content) > max_chars:
            sub_chunks = _chunk_line_windows(
                content,
                file_path,
                language,
                target_chars=min(max_chars, 2500),
                overlap_chars=200,
                max_chars=max_chars,
                symbol_prefix=symbol,
                base_start_line=start,
                symbol_kind=symbol_kind,
            )
            for sub_chunk in sub_chunks:
                sub_chunk.signature = signature
                sub_chunk.metadata = {"graph": graph_metadata}
            chunks.extend(sub_chunks)
            continue

        chunks.append(
            CodeChunk(
                language=language,
                file_path=file_path,
                symbol=symbol,
                start_line=start,
                end_line=end,
                content=content,
                chunk_hash=_hash_text(content),
                signature=signature,
                symbol_kind=symbol_kind,
                metadata={"graph": graph_metadata},
            )
        )
    return chunks


def _build_python_signature(node: ast.AST) -> str:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        arg_names = [arg.arg for arg in node.args.args]
        return f"{node.name}({', '.join(arg_names)})"
    if isinstance(node, ast.ClassDef):
        return f"class {node.name}"
    return ""


def _extract_python_imports(tree: ast.AST) -> list[str]:
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = "." * int(node.level or 0) + (node.module or "")
            for alias in node.names:
                if alias.name == "*":
                    imports.append(f"{module}.*" if module else "*")
                else:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)
    return _dedupe_keep_order(imports)


def _build_python_graph_metadata(node: ast.AST, file_imports: list[str]) -> dict[str, Any]:
    calls = _extract_python_calls(node)
    extends: list[str] = []
    contains: list[str] = []
    if isinstance(node, ast.ClassDef):
        extends = [
            base for base in (_expr_to_dotted(base) for base in node.bases)
            if base
        ]
        contains = [
            getattr(child, "name", "")
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]

    return {
        "symbol": getattr(node, "name", ""),
        "node_type": type(node).__name__,
        "calls": calls,
        "imports": file_imports,
        "extends": _dedupe_keep_order(extends),
        "contains": _dedupe_keep_order([name for name in contains if name]),
    }


def _extract_python_calls(node: ast.AST) -> list[str]:
    calls: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            name = _expr_to_dotted(child.func)
            if name:
                calls.append(name)
    return _dedupe_keep_order(calls)


def _expr_to_dotted(expr: ast.AST) -> str:
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        base = _expr_to_dotted(expr.value)
        return f"{base}.{expr.attr}" if base else expr.attr
    if isinstance(expr, ast.Call):
        return _expr_to_dotted(expr.func)
    if isinstance(expr, ast.Subscript):
        return _expr_to_dotted(expr.value)
    return ""


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        normalized = str(value or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out


def _chunk_line_windows(
    source: str,
    file_path: str,
    language: str,
    *,
    target_chars: int,
    overlap_chars: int,
    max_chars: int,
    symbol_prefix: str = "chunk",
    base_start_line: int = 1,
    symbol_kind: str | None = None,
) -> list[CodeChunk]:
    lines = source.splitlines()
    if not lines:
        return []

    chunks: list[CodeChunk] = []
    start_index = 0
    chunk_idx = 1
    while start_index < len(lines):
        window_start = start_index
        current_chars = 0
        end_index = start_index
        while end_index < len(lines):
            line_len = len(lines[end_index]) + 1
            if current_chars + line_len > target_chars and end_index > start_index:
                break
            current_chars += line_len
            end_index += 1
            if current_chars >= max_chars:
                break

        content = "\n".join(lines[window_start:end_index])
        if content.strip():
            start_line = base_start_line + window_start
            end_line = base_start_line + end_index - 1
            symbol = f"{symbol_prefix}_{chunk_idx}"
            chunks.append(
                CodeChunk(
                    language=language,
                    file_path=file_path,
                    symbol=symbol,
                    start_line=start_line,
                    end_line=end_line,
                    content=content,
                    chunk_hash=_hash_text(content),
                    symbol_kind=symbol_kind or "code",
                )
            )
            chunk_idx += 1

        if end_index >= len(lines):
            break

        overlap_lines = _overlap_line_count(lines, end_index, overlap_chars)
        start_index = max(start_index + 1, end_index - overlap_lines)

    return chunks


def _overlap_line_count(lines: list[str], end_idx: int, overlap_chars: int) -> int:
    chars = 0
    count = 0
    cursor = end_idx - 1
    while cursor >= 0 and chars < overlap_chars:
        chars += len(lines[cursor]) + 1
        count += 1
        cursor -= 1
    return count


def _slice_lines(lines: list[str], start_line: int, end_line: int) -> str:
    start_idx = max(0, start_line - 1)
    end_idx = min(len(lines), end_line)
    return "\n".join(lines[start_idx:end_idx])


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
