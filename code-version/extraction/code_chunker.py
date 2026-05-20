"""AST-first code chunking utilities for code memory ingestion."""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass


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
