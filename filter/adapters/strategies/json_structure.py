"""JSONStructure — replace a JSON blob with its schema + one example value per leaf."""

from __future__ import annotations

import json
from typing import Any

from filter.core.shorter import ShortenResult


def _summarize(node: Any, depth: int, cfg: dict[str, Any], prefix: str = "$") -> list[str]:
    max_depth = int(cfg.get("max_depth", 4))
    max_items = int(cfg.get("max_array_examples", 2))
    preserve = set(cfg.get("preserve_keys", []))

    if depth > max_depth:
        return [f"{prefix}: <truncated at depth {depth}>"]

    if isinstance(node, dict):
        if not node:
            return [f"{prefix}: object (empty)"]
        out = []
        for k in list(node.keys()):
            sub_prefix = f"{prefix}.{k}"
            if k in preserve:
                out.append(f"{sub_prefix}: {json.dumps(node[k])[:200]}")
                continue
            out.extend(_summarize(node[k], depth + 1, cfg, sub_prefix))
        return out

    if isinstance(node, list):
        if not node:
            return [f"{prefix}: array (empty)"]
        out = [f"{prefix}: array (len={len(node)})"]
        for i, item in enumerate(node[:max_items]):
            out.extend(_summarize(item, depth + 1, cfg, f"{prefix}[{i}]"))
        if len(node) > max_items:
            out.append(f"{prefix}[...]: {len(node) - max_items} more item(s)")
        return out

    if isinstance(node, str):
        example = node if len(node) < 60 else node[:57] + "..."
        return [f"{prefix}: string = {example!r}"]

    return [f"{prefix}: {type(node).__name__} = {node!r}"]


class JSONStructureStrategy:
    name = "json_structure"

    def shorten(self, text: str, cfg: dict[str, Any]) -> ShortenResult:
        original = len(text)
        max_total = int(cfg.get("max_total_chars", 4000))
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return ShortenResult(
                text=text, original_chars=original, shortened_chars=original,
                shortening_ratio=1.0, stages_applied=[],
            )
        lines = ["// json_structure: schema + sample values"] + _summarize(data, 0, cfg)
        result = "\n".join(lines)
        if len(result) > max_total:
            result = result[:max_total] + "\n// json_structure: truncated (cap reached)"
        return ShortenResult(
            text=result, original_chars=original, shortened_chars=len(result),
            shortening_ratio=len(result) / original if original else 1.0,
            stages_applied=["json_structure"],
        )