#!/usr/bin/env python3
"""BM25-style reranking variants over the existing RTC offline predictions."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from collections import Counter
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


def q_terms(query: str) -> list[str]:
    return [t for t in base.tokenize(query) if t not in base.STOP_TERMS]


def corpus_stats(snippets: list[Any], field_fn) -> tuple[list[list[str]], Counter[str], float]:
    docs = [field_fn(s) for s in snippets]
    dfs: Counter[str] = Counter()
    for doc in docs:
        for term in set(doc):
            dfs[term] += 1
    avgdl = sum(len(doc) for doc in docs) / max(1, len(docs))
    return docs, dfs, avgdl


def idf(n_docs: int, df: int) -> float:
    return math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))


def bm25_formula(freq: int, dl: int, avgdl: float, *, k1: float = 1.5, b: float = 0.75) -> float:
    denom = freq + k1 * (1.0 - b + b * (dl / max(avgdl, 1e-9)))
    return (freq * (k1 + 1.0)) / max(denom, 1e-9)


def doc_all(snippet: Any) -> list[str]:
    return base.tokenize(" ".join([snippet.rel, snippet.symbol, snippet.signature, snippet.text]))


def bm25_default(snippets: list[Any], query: str) -> dict[str, float]:
    return base.bm25_scores(snippets, query)


def bm25_tuned_short_code(snippets: list[Any], query: str) -> dict[str, float]:
    """Lower b reduces length penalty; lower k1 saturates repeated terms faster."""
    terms = q_terms(query)
    docs, dfs, avgdl = corpus_stats(snippets, doc_all)
    scores: dict[str, float] = {}
    for snippet, doc in zip(snippets, docs):
        tf = Counter(doc)
        score = 0.0
        for term in terms:
            freq = tf.get(term, 0)
            if freq:
                score += idf(len(docs), dfs[term]) * bm25_formula(freq, len(doc), avgdl, k1=0.9, b=0.35)
        if score > 0:
            scores[snippet.uri] = score
    return scores


def bm25_plus(snippets: list[Any], query: str, delta: float = 1.0) -> dict[str, float]:
    """BM25+ lower-bounds matching terms so long documents are not over-penalized."""
    terms = q_terms(query)
    docs, dfs, avgdl = corpus_stats(snippets, doc_all)
    scores: dict[str, float] = {}
    for snippet, doc in zip(snippets, docs):
        tf = Counter(doc)
        score = 0.0
        for term in terms:
            freq = tf.get(term, 0)
            if freq:
                score += idf(len(docs), dfs[term]) * (bm25_formula(freq, len(doc), avgdl) + delta)
        if score > 0:
            scores[snippet.uri] = score
    return scores


def bm25_l(snippets: list[Any], query: str, delta: float = 0.5) -> dict[str, float]:
    """BM25L shifts normalized TF upward for long matching documents."""
    terms = q_terms(query)
    docs, dfs, avgdl = corpus_stats(snippets, doc_all)
    k1 = 1.5
    b = 0.75
    scores: dict[str, float] = {}
    for snippet, doc in zip(snippets, docs):
        tf = Counter(doc)
        dl = len(doc)
        ctd_denom = 1.0 - b + b * (dl / max(avgdl, 1e-9))
        score = 0.0
        for term in terms:
            freq = tf.get(term, 0)
            if not freq:
                continue
            ctd = freq / max(ctd_denom, 1e-9)
            score += idf(len(docs), dfs[term]) * ((k1 + 1.0) * (ctd + delta)) / (k1 + ctd + delta)
        if score > 0:
            scores[snippet.uri] = score
    return scores


def bm25f_code_fields(snippets: list[Any], query: str) -> dict[str, float]:
    """Fielded BM25: symbol/signature/path get stronger weights than body."""
    terms = q_terms(query)
    fields = [
        ("symbol", 3.0, 0.15, lambda s: base.tokenize(s.symbol)),
        ("signature", 2.0, 0.30, lambda s: base.tokenize(s.signature)),
        ("path", 1.4, 0.20, lambda s: base.tokenize(s.rel)),
        ("body", 0.8, 0.75, lambda s: base.tokenize(s.text)),
    ]
    field_docs = []
    for _name, _w, _b, fn in fields:
        docs, dfs, avgdl = corpus_stats(snippets, fn)
        field_docs.append((docs, dfs, avgdl))
    global_docs, global_dfs, _ = corpus_stats(snippets, doc_all)
    scores: dict[str, float] = {}
    for i, snippet in enumerate(snippets):
        score = 0.0
        for term in terms:
            tf_weighted = 0.0
            for (_name, weight, b, _fn), (docs, _dfs, avgdl) in zip(fields, field_docs):
                doc = docs[i]
                freq = Counter(doc).get(term, 0)
                if not freq:
                    continue
                dl = len(doc)
                norm = 1.0 - b + b * (dl / max(avgdl, 1e-9))
                tf_weighted += weight * freq / max(norm, 1e-9)
            if tf_weighted > 0:
                score += idf(len(global_docs), global_dfs[term]) * ((1.5 + 1.0) * tf_weighted) / (1.5 + tf_weighted)
        if score > 0:
            scores[snippet.uri] = score
    return scores


def dirichlet_lm(snippets: list[Any], query: str, mu: float = 1200.0) -> dict[str, float]:
    """Query likelihood with Dirichlet smoothing."""
    terms = q_terms(query)
    docs = [doc_all(s) for s in snippets]
    collection = Counter(term for doc in docs for term in doc)
    collection_len = sum(collection.values())
    scores: dict[str, float] = {}
    for snippet, doc in zip(snippets, docs):
        tf = Counter(doc)
        dl = len(doc)
        score = 0.0
        matched = False
        for term in terms:
            pc = collection.get(term, 0) / max(collection_len, 1)
            if pc <= 0:
                continue
            prob = (tf.get(term, 0) + mu * pc) / (dl + mu)
            score += math.log(max(prob, 1e-12))
            matched = matched or tf.get(term, 0) > 0
        if matched:
            scores[snippet.uri] = math.exp(score / max(1, len(terms)))
    return scores


VARIANTS = {
    "bm25_default": bm25_default,
    "bm25_tuned_short_code": bm25_tuned_short_code,
    "bm25_plus": bm25_plus,
    "bm25_l": bm25_l,
    "bm25f_code_fields": bm25f_code_fields,
    "dirichlet_lm": dirichlet_lm,
}


def evaluate(dataset: Path, predictions: Path, out_dir: Path, top_k: int) -> dict[str, Any]:
    records = [json.loads(line) for line in dataset.read_text().splitlines() if line.strip()]
    pred_rows = [json.loads(line) for line in predictions.read_text().splitlines() if line.strip()]
    by_index = {int(row["record_index"]): row for row in pred_rows}
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {name: {"top1": 0, "top3": 0, "top5": 0} for name in VARIANTS}
    usable = 0
    candidate_union_hit = 0
    pred_path = out_dir / "bm25_variant_union_predictions.jsonl"
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
    parser.add_argument("--out-dir", default=str(ROOT / "artifacts" / "retrieval-bm25-exp"))
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    metrics = evaluate(Path(args.dataset), Path(args.predictions), Path(args.out_dir), args.top_k)
    print(json.dumps(metrics["variants"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
