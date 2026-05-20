"""Shared path-anchor helpers for code-mode retrieval and indexing."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def build_path_anchor_query(rel_posix: str, *, intent: str = "") -> str:
    """Build the file-path anchor string used by code snippet retrieval."""
    q = (rel_posix or "").replace("\\", "/").strip()
    intent_s = (intent or "").strip()
    if not q:
        return intent_s
    needle = Path(q).name
    search_query = intent_s if intent_s else f"{needle} {q}"
    path_slug = q.replace("/", "_").replace(".", "_") if q else ""
    base_slug = needle.replace(".", "_") if needle else ""
    stem = Path(q).stem if q else ""
    extra = [t for t in (path_slug, base_slug, stem) if t]
    if extra:
        tail = " ".join(token for token in extra if token not in search_query.split())
        if tail:
            search_query = f"{search_query} {tail}"
    return search_query.strip()


def grep_style_tokens(pattern: str) -> str:
    """Normalize grep-like patterns into semantic search tokens."""
    if not pattern:
        return ""
    s = str(pattern).strip()
    s = re.sub(r"\(\?:[^)]*\)", " ", s)
    s = s.replace("|", " ").replace("(", " ").replace(")", " ")
    s = s.replace("?", " ").replace("+", " ").replace("*", " ")
    s = re.sub(r"\\[wWdDsS]", " ", s)
    s = re.sub(r"\\[bB]", " ", s)
    s = re.sub(r"\\.", " ", s)
    s = " ".join(s.split())
    return s[:1500]


def guess_repo_rel_from_file_path(file_path: str) -> str:
    """Infer a repo-relative path from an absolute file path."""
    fp = str(file_path or "").strip().replace("\\", "/")
    if not fp:
        return ""
    marker = "/workspace/"
    if marker in fp:
        return fp.split(marker, 1)[1].lstrip("/")
    p = Path(fp)
    parts = p.parts
    if len(parts) >= 2:
        return f"{parts[-2]}/{parts[-1]}"
    return p.name


def prepend_code_location_header(content: str, metadata: dict[str, Any] | None) -> str:
    """Prefix code chunk text with repo-relative path and line range."""
    raw = content if content is not None else ""
    if not metadata:
        return raw
    fp = str(metadata.get("file_path") or "").strip()
    if not fp:
        return raw
    rel = guess_repo_rel_from_file_path(fp)
    path_show = rel if rel else fp.replace("\\", "/")
    sl = metadata.get("start_line")
    el = metadata.get("end_line")
    try:
        sl_i = int(sl) if sl is not None else None
        el_i = int(el) if el is not None else None
    except (TypeError, ValueError):
        sl_i = el_i = None
    if sl_i is not None and el_i is not None:
        head = f"# {path_show} (lines {sl_i}-{el_i})\n\n"
    else:
        head = f"# {path_show}\n\n"
    if raw.startswith(head):
        return raw
    return head + raw
