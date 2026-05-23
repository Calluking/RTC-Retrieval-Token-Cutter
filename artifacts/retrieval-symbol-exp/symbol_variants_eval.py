#!/usr/bin/env python3
"""Symbol/ctags-style reranking variants over existing RTC predictions."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EVAL_PATH = ROOT / "artifacts" / "retrieval-eval" / "offline_retrieval_eval.py"
spec = importlib.util.spec_from_file_location("offline_retrieval_eval", EVAL_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot import {EVAL_PATH}")
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)


CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|[_\W]+")


def snippet_from_hit(hit: dict[str, Any]) -> Any:
    return base.Snippet(
        uri=str(hit.get("uri") or ""),
        rel=str(hit.get("rel") or ""),
        symbol=str(hit.get("symbol") or ""),
        kind=str(hit.get("kind") or "code"),
        start_line=int(hit.get("start_line") or 1),
        end_line=int(hit.get("end_line") or hit.get("start_line") or 1),
        signature=str(hit.get("signature") or ""),
        text=str(hit.get("text") or ""),
    )


def split_identifier(text: str) -> list[str]:
    parts: list[str] = []
    for raw in re.split(CAMEL_RE, text or ""):
        if not raw:
            continue
        for token in base.tokenize(raw):
            if token and token not in base.STOP_TERMS:
                parts.append(token)
    return parts


def query_terms(query: str) -> list[str]:
    return [t for t in base.extract_query_terms(query) if t not in base.STOP_TERMS]


def exact_ctags(snippets: list[Any], query: str) -> dict[str, float]:
    return base.ctags_scores(snippets, query)


def identifier_subtoken(snippets: list[Any], query: str) -> dict[str, float]:
    """Match query terms against camel/snake-case pieces of symbols."""
    terms = query_terms(query)
    scores: dict[str, float] = {}
    for snippet in snippets:
        symbol_parts = split_identifier(snippet.symbol)
        sig_parts = split_identifier(snippet.signature)
        path_parts = split_identifier(snippet.rel)
        score = 0.0
        for term in terms:
            if term in symbol_parts:
                score += 2.4
            if term in sig_parts:
                score += 1.4
            if term in path_parts:
                score += 0.8
            if any(term in part or part in term for part in symbol_parts if len(part) >= 3):
                score += 0.8
        if score > 0:
            scores[snippet.uri] = score
    return scores


def fuzzy_symbol(snippets: list[Any], query: str) -> dict[str, float]:
    """Use sequence similarity for typo/partial symbol matches."""
    terms = query_terms(query)
    q_join = "".join(terms)
    scores: dict[str, float] = {}
    for snippet in snippets:
        candidates = [
            (snippet.symbol, 3.0),
            (snippet.signature, 1.6),
            (Path(snippet.rel).stem, 1.2),
        ]
        score = 0.0
        for cand, weight in candidates:
            cand_norm = "".join(split_identifier(cand))
            if not cand_norm or not q_join:
                continue
            ratio = SequenceMatcher(None, q_join, cand_norm).ratio()
            if ratio >= 0.45:
                score += weight * ratio
            for term in terms:
                best = max((SequenceMatcher(None, term, part).ratio() for part in split_identifier(cand)), default=0.0)
                if best >= 0.72:
                    score += weight * best * 0.5
        if score > 0:
            scores[snippet.uri] = score
    return scores


def acronym_abbrev(snippets: list[Any], query: str) -> dict[str, float]:
    """Handle abbreviations like FSP -> FileStoragePermissions."""
    terms = query_terms(query)
    q_acronyms = set(terms)
    q_acronyms.add("".join(term[:1] for term in terms if term))
    scores: dict[str, float] = {}
    for snippet in snippets:
        fields = [
            (split_identifier(snippet.symbol), 3.0),
            (split_identifier(snippet.signature), 1.6),
            (split_identifier(snippet.rel), 1.0),
        ]
        score = 0.0
        for parts, weight in fields:
            if not parts:
                continue
            acronym = "".join(part[:1] for part in parts)
            joined = "".join(parts)
            for q in q_acronyms:
                if len(q) >= 2 and q == acronym:
                    score += weight * 1.4
                elif len(q) >= 3 and q in joined:
                    score += weight * 0.7
        if score > 0:
            scores[snippet.uri] = score
    return scores


def kind_aware_symbol(snippets: list[Any], query: str) -> dict[str, float]:
    """Boost symbol matches whose kind agrees with query intent."""
    terms = query_terms(query)
    q_l = query.lower()
    kind_boosts = {
        "type": 1.3 if any(w in q_l for w in ("class", "type", "object")) else 1.0,
        "function": 1.3 if any(w in q_l for w in ("def", "function", "method", "call")) else 1.0,
        "assignment": 1.25 if any(w in q_l for w in ("setting", "constant", "attribute", "variable", "default")) else 1.0,
    }
    base_scores = identifier_subtoken(snippets, query)
    scores: dict[str, float] = {}
    by_uri = {s.uri: s for s in snippets}
    for uri, score in base_scores.items():
        snippet = by_uri[uri]
        scores[uri] = score * kind_boosts.get(snippet.kind, 1.0)
        if snippet.kind in {"type", "function", "assignment"} and snippet.kind in terms:
            scores[uri] += 1.0
    return scores


def symbol_graph_neighbor(snippets: list[Any], query: str) -> dict[str, float]:
    """Anchor by symbol match, then expand to nearby same-file symbols."""
    anchors = identifier_subtoken(snippets, query)
    by_file: dict[str, list[Any]] = {}
    by_uri = {s.uri: s for s in snippets}
    for snippet in snippets:
        by_file.setdefault(snippet.rel, []).append(snippet)
    scores = dict(anchors)
    for uri, score in anchors.items():
        anchor = by_uri.get(uri)
        if not anchor:
            continue
        for neighbor in by_file.get(anchor.rel, []):
            if neighbor.uri == uri:
                continue
            dist = abs(neighbor.start_line - anchor.start_line)
            if dist > 120:
                continue
            scores[neighbor.uri] = max(scores.get(neighbor.uri, 0.0), score * 0.45 + 1.0 / (1.0 + dist / 30.0))
    return scores


def combine_scores(*maps: tuple[dict[str, float], float]) -> dict[str, float]:
    out: dict[str, float] = {}
    for scores, weight in maps:
        if not scores:
            continue
        vals = list(scores.values())
        lo, hi = min(vals), max(vals)
        for uri, value in scores.items():
            norm = 1.0 if hi <= lo else (value - lo) / (hi - lo)
            out[uri] = out.get(uri, 0.0) + weight * norm
    return out


def ctags_plus_subtoken(snippets: list[Any], query: str) -> dict[str, float]:
    return combine_scores(
        (exact_ctags(snippets, query), 0.7),
        (identifier_subtoken(snippets, query), 0.3),
    )


def ctags_plus_fuzzy(snippets: list[Any], query: str) -> dict[str, float]:
    return combine_scores(
        (exact_ctags(snippets, query), 0.75),
        (fuzzy_symbol(snippets, query), 0.25),
    )


def all_symbol_features(snippets: list[Any], query: str) -> dict[str, float]:
    return combine_scores(
        (exact_ctags(snippets, query), 0.55),
        (identifier_subtoken(snippets, query), 0.2),
        (fuzzy_symbol(snippets, query), 0.15),
        (acronym_abbrev(snippets, query), 0.05),
        (kind_aware_symbol(snippets, query), 0.05),
    )


VARIANTS = {
    "ctags_default": exact_ctags,
    "ctags_plus_subtoken": ctags_plus_subtoken,
    "ctags_plus_fuzzy": ctags_plus_fuzzy,
    "all_symbol_features": all_symbol_features,
    "identifier_subtoken": identifier_subtoken,
    "fuzzy_symbol": fuzzy_symbol,
    "acronym_abbrev": acronym_abbrev,
    "kind_aware_symbol": kind_aware_symbol,
    "symbol_graph_neighbor": symbol_graph_neighbor,
}


def evaluate(dataset: Path, predictions: Path, out_dir: Path, top_k: int) -> dict[str, Any]:
    records = [json.loads(line) for line in dataset.read_text().splitlines() if line.strip()]
    pred_rows = [json.loads(line) for line in predictions.read_text().splitlines() if line.strip()]
    by_index = {int(row["record_index"]): row for row in pred_rows}
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {name: {"top1": 0, "top3": 0, "top5": 0} for name in VARIANTS}
    usable = 0
    candidate_union_hit = 0
    pred_path = out_dir / "symbol_variant_union_predictions.jsonl"
    with pred_path.open("w", encoding="utf-8") as handle:
        for idx, record in enumerate(records, start=1):
            pred = by_index.get(idx)
            if not pred:
                continue
            query = str((record.get("search") or {}).get("query") or pred.get("query") or "")
            targets = pred.get("targets") or base.positive_targets(record)
            if not query or not targets:
                continue
            snippets_by_uri: dict[str, Any] = {}
            for hits in (pred.get("hits_by_route") or {}).values():
                for hit in hits:
                    uri = str(hit.get("uri") or "")
                    if uri and uri not in snippets_by_uri:
                        snippets_by_uri[uri] = snippet_from_hit(hit)
            snippets = list(snippets_by_uri.values())
            if not snippets:
                continue
            usable += 1
            candidate_union_hit += int(any(
                base.hit_target(base.snippet_dict(snippet, 1.0), targets, False)
                for snippet in snippets
            ))
            row = {
                "record_index": idx,
                "instance_id": record.get("instance_id"),
                "query": query,
                "targets": targets,
                "candidate_count": len(snippets),
                "variants": {},
            }
            for name, scorer in VARIANTS.items():
                hits = base.rank_route(snippets, scorer(snippets, query), max(top_k, 5))
                metrics = {
                    "top1": any(base.hit_target(hit, targets, False) for hit in hits[:1]),
                    "top3": any(base.hit_target(hit, targets, False) for hit in hits[:3]),
                    "top5": any(base.hit_target(hit, targets, False) for hit in hits[:5]),
                }
                for key, value in metrics.items():
                    counts[name][key] += int(value)
                row["variants"][name] = {"metrics": metrics, "hits": hits[:5]}
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    table = []
    for name, route_counts in counts.items():
        table.append({
            "variant": name,
            "top1": round(route_counts["top1"] / usable, 4),
            "top3": round(route_counts["top3"] / usable, 4),
            "top5": round(route_counts["top5"] / usable, 4),
            "top1_count": route_counts["top1"],
            "top3_count": route_counts["top3"],
            "top5_count": route_counts["top5"],
        })
    table.sort(key=lambda row: (row["top5"], row["top3"], row["top1"]), reverse=True)
    metrics = {
        "dataset": str(dataset),
        "source_predictions": str(predictions),
        "predictions": str(pred_path),
        "usable_records": usable,
        "candidate_union_recall": round(candidate_union_hit / usable, 4),
        "experiment_scope": "rerank_existing_4_route_top5_union",
        "variants": table,
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    lines = [
        "| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in table:
        lines.append(
            f"| {row['variant']} | {row['top1']:.4f} | {row['top3']:.4f} | {row['top5']:.4f} | "
            f"{row['top1_count']} | {row['top3_count']} | {row['top5_count']} |"
        )
    (out_dir / "route_accuracy.md").write_text("\n".join(lines) + "\n")
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(ROOT / "artifacts" / "legacy-search-dataset" / "search_targets.jsonl"))
    parser.add_argument("--predictions", default=str(ROOT / "artifacts" / "retrieval-eval" / "predictions.jsonl"))
    parser.add_argument("--out-dir", default=str(ROOT / "artifacts" / "retrieval-symbol-exp"))
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    metrics = evaluate(Path(args.dataset), Path(args.predictions), Path(args.out_dir), args.top_k)
    print(json.dumps(metrics["variants"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
