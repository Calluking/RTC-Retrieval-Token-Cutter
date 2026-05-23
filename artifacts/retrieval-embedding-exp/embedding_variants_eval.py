#!/usr/bin/env python3
"""Embedding-route variants for the legacy grep target dataset.

This stays artifact-side on purpose: it reuses the existing offline evaluator's
candidate collection/chunking and compares embedding-like scorers only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
EVAL_PATH = ROOT / "artifacts" / "retrieval-eval" / "offline_retrieval_eval.py"
spec = importlib.util.spec_from_file_location("offline_retrieval_eval", EVAL_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot import {EVAL_PATH}")
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)


TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|0o[0-7]+|\d+")


def tokens(text: str) -> list[str]:
    return base.tokenize(text or "")


def counter_cosine(query_terms: list[str], doc_terms: list[str]) -> float:
    q = Counter(query_terms)
    d = Counter(doc_terms)
    if not q or not d:
        return 0.0
    dot = sum(q.get(term, 0) * freq for term, freq in d.items())
    if dot <= 0:
        return 0.0
    q_norm = math.sqrt(sum(v * v for v in q.values()))
    d_norm = math.sqrt(sum(v * v for v in d.values()))
    return dot / max(q_norm * d_norm, 1e-9)


def doc_terms(snippet: Any) -> list[str]:
    return tokens(" ".join([snippet.rel, snippet.symbol, snippet.signature, snippet.text]))


def baseline(snippets: list[Any], record: dict[str, Any], query: str) -> dict[str, float]:
    return base.embedding_proxy_scores(snippets, query)


def query_with_issue(snippets: list[Any], record: dict[str, Any], query: str) -> dict[str, float]:
    issue = str(record.get("problem_statement") or "")
    expanded = " ".join([query, issue[:1200]])
    q_terms = tokens(expanded)
    return {
        snippet.uri: score
        for snippet in snippets
        if (score := counter_cosine(q_terms, doc_terms(snippet))) > 0
    }


def query_with_scope(snippets: list[Any], record: dict[str, Any], query: str) -> dict[str, float]:
    search = record.get("search") or {}
    path = str(search.get("path") or "")
    command = str(search.get("command") or "")
    path_bits = " ".join(Path(part).name for part in re.split(r"\s+", path + " " + command) if "/" in part)
    expanded = " ".join([query, path, path_bits])
    q_terms = tokens(expanded)
    return {
        snippet.uri: score
        for snippet in snippets
        if (score := counter_cosine(q_terms, doc_terms(snippet))) > 0
    }


def field_weighted(snippets: list[Any], record: dict[str, Any], query: str) -> dict[str, float]:
    q_terms = tokens(query)
    scores: dict[str, float] = {}
    for snippet in snippets:
        rel_score = counter_cosine(q_terms, tokens(snippet.rel)) * 1.8
        symbol_score = counter_cosine(q_terms, tokens(snippet.symbol)) * 2.4
        sig_score = counter_cosine(q_terms, tokens(snippet.signature)) * 1.6
        body_score = counter_cosine(q_terms, tokens(snippet.text)) * 0.8
        score = rel_score + symbol_score + sig_score + body_score
        if score > 0:
            scores[snippet.uri] = score
    return scores


def prf_expand(snippets: list[Any], record: dict[str, Any], query: str) -> dict[str, float]:
    """Pseudo relevance feedback: expand query from top lexical snippets."""
    bm25 = base.bm25_scores(snippets, query)
    top = sorted(bm25.items(), key=lambda item: item[1], reverse=True)[:3]
    by_uri = {snippet.uri: snippet for snippet in snippets}
    original = set(tokens(query))
    extra: Counter[str] = Counter()
    for uri, _ in top:
        snippet = by_uri.get(uri)
        if not snippet:
            continue
        for term in tokens(" ".join([snippet.rel, snippet.symbol, snippet.signature])):
            if len(term) >= 3 and term not in base.STOP_TERMS:
                extra[term] += 1
    expansion = [term for term, _ in extra.most_common(10) if term not in original]
    q_terms = tokens(" ".join([query, " ".join(expansion)]))
    return {
        snippet.uri: score
        for snippet in snippets
        if (score := counter_cosine(q_terms, doc_terms(snippet))) > 0
    }


def late_interaction(snippets: list[Any], record: dict[str, Any], query: str) -> dict[str, float]:
    """Cheap ColBERT-ish proxy: sum best per-query-token field matches."""
    q_terms = [term for term in base.extract_query_terms(query) if term]
    scores: dict[str, float] = {}
    for snippet in snippets:
        fields = [
            (tokens(snippet.symbol), 2.2),
            (tokens(snippet.signature), 1.8),
            (tokens(snippet.rel), 1.5),
            (tokens(snippet.text), 0.7),
        ]
        score = 0.0
        for q in q_terms:
            best = 0.0
            for f_terms, weight in fields:
                if q in f_terms:
                    best = max(best, weight)
                elif any(q in ft or ft in q for ft in f_terms if len(ft) >= 3 and len(q) >= 3):
                    best = max(best, weight * 0.55)
            score += best
        if score > 0:
            # Mild length normalization: avoid huge classes winning only by body size.
            scores[snippet.uri] = score / (1.0 + math.log1p(max(1, len(tokens(snippet.text)))) * 0.08)
    return scores


VARIANTS: dict[str, Callable[[list[Any], dict[str, Any], str], dict[str, float]]] = {
    "baseline_embedding_proxy": baseline,
    "query_plus_issue": query_with_issue,
    "query_plus_legacy_scope": query_with_scope,
    "field_weighted_embedding": field_weighted,
    "pseudo_relevance_feedback": prf_expand,
    "late_interaction_proxy": late_interaction,
}


def evaluate(dataset: Path, out_dir: Path, candidate_limit: int, top_k: int) -> dict[str, Any]:
    rows = [json.loads(line) for line in dataset.read_text().splitlines() if line.strip()]
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {name: {"top1": 0, "top3": 0, "top5": 0} for name in VARIANTS}
    usable = 0
    candidate_hit = 0
    pred_path = out_dir / "embedding_variant_predictions.jsonl"
    with pred_path.open("w", encoding="utf-8") as handle:
        for idx, record in enumerate(rows, start=1):
            root = Path(record.get("workspace") or "")
            query = str((record.get("search") or {}).get("query") or "")
            targets = base.positive_targets(record)
            if not root.is_dir() or not query or not targets:
                continue
            usable += 1
            candidate_files = base.collect_candidate_files(root, query, candidate_limit)
            candidate_hit += int(any(target["path"] in candidate_files for target in targets))
            snippets = base.build_snippets(root, candidate_files)
            row = {
                "record_index": idx,
                "instance_id": record.get("instance_id"),
                "query": query,
                "targets": targets,
                "candidate_count": len(candidate_files),
                "variants": {},
            }
            for name, scorer in VARIANTS.items():
                hits = base.rank_route(snippets, scorer(snippets, record, query), max(top_k, 5))
                metrics = {
                    "top1": any(base.hit_target(hit, targets, False) for hit in hits[:1]),
                    "top3": any(base.hit_target(hit, targets, False) for hit in hits[:3]),
                    "top5": any(base.hit_target(hit, targets, False) for hit in hits[:5]),
                }
                for key, value in metrics.items():
                    counts[name][key] += int(value)
                row["variants"][name] = {
                    "metrics": metrics,
                    "hits": hits[:5],
                }
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
        "predictions": str(pred_path),
        "usable_records": usable,
        "candidate_limit": candidate_limit,
        "candidate_recall": round(candidate_hit / usable, 4),
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


def evaluate_from_predictions(dataset: Path, predictions: Path, out_dir: Path, top_k: int) -> dict[str, Any]:
    """Fast experiment over the existing 4-route top-5 union.

    This tests whether an embedding-side scorer improves candidate ordering once
    the current retriever has already produced its final rerank pool.
    """
    records = [json.loads(line) for line in dataset.read_text().splitlines() if line.strip()]
    pred_rows = [json.loads(line) for line in predictions.read_text().splitlines() if line.strip()]
    by_index = {int(row["record_index"]): row for row in pred_rows}
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {name: {"top1": 0, "top3": 0, "top5": 0} for name in VARIANTS}
    usable = 0
    candidate_union_hit = 0
    pred_path = out_dir / "embedding_variant_union_predictions.jsonl"
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
                hits = base.rank_route(snippets, scorer(snippets, record, query), max(top_k, 5))
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
    parser.add_argument("--out-dir", default=str(ROOT / "artifacts" / "retrieval-embedding-exp"))
    parser.add_argument("--predictions", default=str(ROOT / "artifacts" / "retrieval-eval" / "predictions.jsonl"))
    parser.add_argument("--from-predictions", action="store_true")
    parser.add_argument("--candidate-limit", type=int, default=80)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    if args.from_predictions:
        metrics = evaluate_from_predictions(Path(args.dataset), Path(args.predictions), Path(args.out_dir), args.top_k)
    else:
        metrics = evaluate(Path(args.dataset), Path(args.out_dir), args.candidate_limit, args.top_k)
    print(json.dumps(metrics["variants"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
