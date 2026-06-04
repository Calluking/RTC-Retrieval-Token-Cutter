"""AST-first code chunking utilities for code memory ingestion."""

from __future__ import annotations

import ast
import hashlib
import re
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
    if lower.endswith(".md") or lower.endswith(".markdown"):
        return "markdown"
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
    if lang == "markdown":
        chunks = _chunk_markdown_api_entries(source, file_path, target_chars=target_chars)
        if chunks:
            return chunks
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


_MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_MD_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_MD_API_HEADING_RE = re.compile(
    r"\b(class|interface|struct|enum|func|operator|macro|let|var|prop|const|init|extend)\b|"
    r"^\s*(static\s+)?(func|class|interface|struct|enum|operator|let|var)\s+",
    re.IGNORECASE,
)
_MD_SIGNATURE_RE = re.compile(
    r"\b(public|private|protected|static|mut|foreign|unsafe|open|abstract|override)?\s*"
    r"(func|class|interface|struct|enum|operator|let|var|macro|extend)\b"
)
_MD_API_LABEL_RE = re.compile(
    r"^(\*\*)?(功能|参数|返回值|异常|错误码|示例|描述|说明|约束|权限|起始版本|"
    r"Function|Parameters|Return|Returns|Throws|Example|Description|"
    r"Required permissions|System capability)",
    re.IGNORECASE,
)
_MD_GENERIC_CONTAINER_TITLE_RE = re.compile(
    r"^(类|函数|接口|结构体|枚举|异常类|宏|常量|变量|"
    r"Classes?|Functions?|Interfaces?|Structs?|Enums?|Exceptions?|Macros?|Constants?|Variables?)$",
    re.IGNORECASE,
)
_MD_API_PART_TITLE_RE = re.compile(
    r"^(功能|参数|返回值|异常|错误码|示例|描述|说明|约束|权限|起始版本|"
    r"Function|Parameters?|Returns?|Throws|Examples?|Description|"
    r"Required permissions|System capability)$",
    re.IGNORECASE,
)


def _chunk_markdown_api_entries(
    source: str,
    file_path: str,
    *,
    target_chars: int,
) -> list[CodeChunk]:
    lines = source.splitlines()
    if not lines:
        return []

    heading_paths = _markdown_heading_paths(lines)
    entries = _detect_markdown_api_entries(lines)
    atomic_regions = _markdown_fenced_regions(lines) + _markdown_table_regions(lines)
    chunks: list[CodeChunk] = []
    covered: list[tuple[int, int]] = []

    for start_idx, end_idx, title in entries:
        start_idx, end_idx = _extend_over_markdown_atomic_blocks(start_idx, end_idx, atomic_regions)
        chunk = _markdown_chunk_from_range(
            lines,
            file_path,
            start_idx,
            end_idx,
            title=title,
            heading_paths=heading_paths,
            target_chars=target_chars,
        )
        if chunk:
            chunks.append(chunk)
            covered.append((start_idx, end_idx))

    # Keep non-API Markdown discoverable with ordinary windows, without cutting
    # into API-entry chunks.
    cursor = 0
    for start_idx, end_idx in sorted(covered):
        if cursor < start_idx:
            chunks.extend(
                _chunk_markdown_gap(
                    lines,
                    file_path,
                    cursor,
                    start_idx,
                    heading_paths=heading_paths,
                    target_chars=target_chars,
                )
            )
        cursor = max(cursor, end_idx)
    if cursor < len(lines):
        chunks.extend(
            _chunk_markdown_gap(
                lines,
                file_path,
                cursor,
                len(lines),
                heading_paths=heading_paths,
                target_chars=target_chars,
            )
        )

    chunks.sort(key=lambda item: (item.start_line, item.end_line, item.symbol))
    return chunks


def _clean_markdown_heading(text: str) -> str:
    text = re.sub(r"\[[^\]]+\]\([^)]+\)", lambda m: m.group(0).split("](", 1)[0][1:], text)
    text = re.sub(r"[`*_#<>]", "", text)
    return " ".join(text.strip().split())


def _markdown_heading_paths(lines: list[str]) -> list[list[str]]:
    stack: list[str] = []
    out: list[list[str]] = []
    in_fence = False
    for line in lines:
        if _MD_FENCE_RE.match(line):
            in_fence = not in_fence
        if not in_fence:
            match = _MD_HEADING_RE.match(line)
            if match:
                level = len(match.group(1))
                stack = stack[: level - 1]
                stack.append(_clean_markdown_heading(match.group(2)))
        out.append(list(stack))
    return out


def _markdown_heading_ranges(lines: list[str]) -> list[tuple[int, int, str, int]]:
    headings: list[tuple[int, int, str]] = []
    in_fence = False
    for idx, line in enumerate(lines):
        if _MD_FENCE_RE.match(line):
            in_fence = not in_fence
        if in_fence:
            continue
        match = _MD_HEADING_RE.match(line)
        if match:
            headings.append((idx, len(match.group(1)), _clean_markdown_heading(match.group(2))))

    ranges: list[tuple[int, int, str, int]] = []
    for index, (start_idx, level, title) in enumerate(headings):
        end_idx = len(lines)
        for next_start, next_level, _ in headings[index + 1:]:
            if next_level <= level:
                end_idx = next_start
                break
        ranges.append((start_idx, end_idx, title, level))
    return ranges


def _detect_markdown_api_entries(lines: list[str]) -> list[tuple[int, int, str]]:
    entries: list[tuple[int, int, str]] = []
    for start_idx, end_idx, title, _level in _markdown_heading_ranges(lines):
        if _MD_GENERIC_CONTAINER_TITLE_RE.match(title):
            continue
        sample = "\n".join(lines[start_idx:min(end_idx, start_idx + 120)])
        api_title = bool(_MD_API_HEADING_RE.search(title))
        if not api_title and _MD_API_PART_TITLE_RE.match(title):
            continue
        if not (api_title or _MD_SIGNATURE_RE.search(sample) or _MD_API_LABEL_RE.search(sample)):
            continue
        if end_idx - start_idx >= 4:
            entries.append((start_idx, end_idx, title))
    return entries


def _markdown_fenced_regions(lines: list[str]) -> list[tuple[int, int]]:
    regions: list[tuple[int, int]] = []
    start_idx: int | None = None
    for idx, line in enumerate(lines):
        if not _MD_FENCE_RE.match(line):
            continue
        if start_idx is None:
            start_idx = idx
        else:
            regions.append((start_idx, idx + 1))
            start_idx = None
    if start_idx is not None:
        regions.append((start_idx, len(lines)))
    return regions


def _markdown_is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def _markdown_table_regions(lines: list[str]) -> list[tuple[int, int]]:
    regions: list[tuple[int, int]] = []
    idx = 0
    while idx < len(lines):
        if not _markdown_is_table_line(lines[idx]):
            idx += 1
            continue
        start_idx = idx
        while idx < len(lines) and _markdown_is_table_line(lines[idx]):
            idx += 1
        if idx - start_idx >= 2:
            regions.append((start_idx, idx))
    return regions


def _extend_over_markdown_atomic_blocks(
    start_idx: int,
    end_idx: int,
    regions: list[tuple[int, int]],
) -> tuple[int, int]:
    changed = True
    while changed:
        changed = False
        for region_start, region_end in regions:
            if max(start_idx, region_start) >= min(end_idx, region_end):
                continue
            if start_idx > region_start:
                start_idx = region_start
                changed = True
            if end_idx < region_end:
                end_idx = region_end
                changed = True
    return start_idx, end_idx


def _markdown_chunk_from_range(
    lines: list[str],
    file_path: str,
    start_idx: int,
    end_idx: int,
    *,
    title: str,
    heading_paths: list[list[str]],
    target_chars: int,
) -> CodeChunk | None:
    content = "\n".join(lines[start_idx:end_idx]).strip()
    if not content:
        return None
    heading_path = heading_paths[min(start_idx, len(heading_paths) - 1)] if heading_paths else []
    if not heading_path and title:
        heading_path = [title]
    kind = "markdown_api_entry_oversize" if len(content) > target_chars else "markdown_api_entry"
    metadata = {
        "heading_path": heading_path,
        "markdown": {
            "heading_path": heading_path,
            "title": title,
            "oversize": len(content) > target_chars,
        },
        "graph": {
            "symbol": title,
            "node_type": "MarkdownApiEntry",
            "calls": [],
            "imports": [],
            "extends": [],
            "contains": heading_path[:-1],
        },
    }
    return CodeChunk(
        language="markdown",
        file_path=file_path,
        symbol=title or f"markdown_{start_idx + 1}_{end_idx}",
        start_line=start_idx + 1,
        end_line=end_idx,
        content=content,
        chunk_hash=_hash_text(content),
        signature=" / ".join(heading_path),
        symbol_kind=kind,
        metadata=metadata,
    )


def _chunk_markdown_gap(
    lines: list[str],
    file_path: str,
    start_idx: int,
    end_idx: int,
    *,
    heading_paths: list[list[str]],
    target_chars: int,
) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    cursor = start_idx
    chunk_index = 1
    while cursor < end_idx:
        window_start = cursor
        chars = 0
        while cursor < end_idx:
            line_len = len(lines[cursor]) + 1
            if chars + line_len > target_chars and cursor > window_start:
                break
            chars += line_len
            cursor += 1
        content = "\n".join(lines[window_start:cursor]).strip()
        if content:
            heading_path = heading_paths[min(window_start, len(heading_paths) - 1)] if heading_paths else []
            title = heading_path[-1] if heading_path else f"markdown_{chunk_index}"
            chunks.append(
                CodeChunk(
                    language="markdown",
                    file_path=file_path,
                    symbol=title,
                    start_line=window_start + 1,
                    end_line=cursor,
                    content=content,
                    chunk_hash=_hash_text(content),
                    signature=" / ".join(heading_path),
                    symbol_kind="markdown_text",
                    metadata={
                        "heading_path": heading_path,
                        "markdown": {"heading_path": heading_path, "title": title, "oversize": False},
                        "graph": {
                            "symbol": title,
                            "node_type": "MarkdownText",
                            "calls": [],
                            "imports": [],
                            "extends": [],
                            "contains": heading_path[:-1],
                        },
                    },
                )
            )
            chunk_index += 1
        if cursor >= end_idx:
            break
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
