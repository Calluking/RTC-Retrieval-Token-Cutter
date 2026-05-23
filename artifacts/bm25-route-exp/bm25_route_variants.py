#!/usr/bin/env python3
"""Canonical BM25-route variants.

Metric:
  grep candidate pool -> BM25-family variant ranks snippets independently
  -> top1/top3/top5 hit
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]


def import_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


base = import_module("offline_retrieval_eval", ROOT / "artifacts" / "retrieval-eval" / "offline_retrieval_eval.py")
bm25_old = import_module("bm25_variants_eval", ROOT / "artifacts" / "retrieval-bm25-exp" / "bm25_variants_eval.py")
graph_mem = import_module("graph_memory_variants_eval", ROOT / "artifacts" / "retrieval-graph-memory-exp" / "graph_memory_variants_eval.py")


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


def bm25f(snippets: list[Any], query: str, fields: list[tuple[str, float, float, Callable[[Any], list[str]]]], *, k1: float = 1.5) -> dict[str, float]:
    terms = q_terms(query)
    field_docs = []
    for _name, _weight, _b, fn in fields:
        field_docs.append(corpus_stats(snippets, fn))
    global_docs, global_dfs, _ = corpus_stats(snippets, lambda s: base.tokenize(" ".join([s.rel, s.symbol, s.signature, s.text])))
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
                score += idf(len(global_docs), global_dfs[term]) * ((k1 + 1.0) * tf_weighted) / (k1 + tf_weighted)
        if score > 0:
            scores[snippet.uri] = score
    return scores


def bm25f_current(snippets: list[Any], query: str) -> dict[str, float]:
    return bm25_old.bm25f_code_fields(snippets, query)


def bm25f_symbol_heavy(snippets: list[Any], query: str) -> dict[str, float]:
    fields = [
        ("symbol", 4.5, 0.05, lambda s: base.tokenize(s.symbol)),
        ("signature", 2.6, 0.20, lambda s: base.tokenize(s.signature)),
        ("path", 1.2, 0.20, lambda s: base.tokenize(s.rel)),
        ("body", 0.45, 0.65, lambda s: base.tokenize(s.text)),
    ]
    return bm25f(snippets, query, fields)


def bm25f_path_heavy(snippets: list[Any], query: str) -> dict[str, float]:
    fields = [
        ("path", 3.2, 0.05, lambda s: base.tokenize(s.rel)),
        ("symbol", 2.6, 0.10, lambda s: base.tokenize(s.symbol)),
        ("signature", 1.8, 0.25, lambda s: base.tokenize(s.signature)),
        ("body", 0.55, 0.70, lambda s: base.tokenize(s.text)),
    ]
    return bm25f(snippets, query, fields)


def bm25f_no_body(snippets: list[Any], query: str) -> dict[str, float]:
    fields = [
        ("symbol", 4.0, 0.05, lambda s: base.tokenize(s.symbol)),
        ("signature", 2.8, 0.15, lambda s: base.tokenize(s.signature)),
        ("path", 2.0, 0.10, lambda s: base.tokenize(s.rel)),
    ]
    return bm25f(snippets, query, fields)


def bm25f_identifier_summary(snippets: list[Any], query: str) -> dict[str, float]:
    def identifiers(s: Any) -> list[str]:
        text = " ".join([s.rel, s.symbol, s.signature, s.text])
        toks = base.tokenize(text)
        expanded = []
        for token in toks:
            expanded.append(token)
            if "_" in token:
                expanded.extend(part for part in token.split("_") if part)
        return expanded

    fields = [
        ("symbol", 3.5, 0.05, lambda s: base.tokenize(s.symbol)),
        ("signature", 2.2, 0.20, lambda s: base.tokenize(s.signature)),
        ("path", 1.6, 0.15, lambda s: base.tokenize(s.rel)),
        ("identifiers", 0.9, 0.35, identifiers),
    ]
    return bm25f(snippets, query, fields, k1=1.1)


def bm25_field_rrf(snippets: list[Any], query: str) -> dict[str, float]:
    field_scores = [
        bm25f(snippets, query, [("symbol", 1.0, 0.05, lambda s: base.tokenize(s.symbol))]),
        bm25f(snippets, query, [("signature", 1.0, 0.15, lambda s: base.tokenize(s.signature))]),
        bm25f(snippets, query, [("path", 1.0, 0.10, lambda s: base.tokenize(s.rel))]),
        bm25f(snippets, query, [("body", 1.0, 0.75, lambda s: base.tokenize(s.text))]),
    ]
    out: dict[str, float] = defaultdict(float)
    for scores in field_scores:
        for rank, (uri, _score) in enumerate(sorted(scores.items(), key=lambda item: item[1], reverse=True), start=1):
            out[uri] += 1.0 / (60.0 + rank)
    return dict(out)


VARIANTS = {
    "bm25f_code_fields_current": bm25f_current,
    "bm25f_symbol_heavy": bm25f_symbol_heavy,
    "bm25f_path_heavy": bm25f_path_heavy,
    "bm25f_no_body": bm25f_no_body,
    "bm25f_identifier_summary": bm25f_identifier_summary,
    "bm25_field_rrf": bm25_field_rrf,
    "bm25_default": bm25_old.bm25_default,
}


def hit_metrics(hits: list[dict[str, Any]], targets: list[dict[str, Any]]) -> dict[str, bool]:
    return {
        "top1": any(base.hit_target(hit, targets, False) for hit in hits[:1]),
        "top3": any(base.hit_target(hit, targets, False) for hit in hits[:3]),
        "top5": any(base.hit_target(hit, targets, False) for hit in hits[:5]),
    }


def evaluate(dataset: Path, out_dir: Path, candidate_limit: int, max_snippets: int) -> dict[str, Any]:
    rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {name: {"top1": 0, "top3": 0, "top5": 0} for name in VARIANTS}
    timings = defaultdict(float)
    usable = 0
    candidate_hit = 0
    pred_path = out_dir / "bm25_route_predictions.jsonl"
    with pred_path.open("w", encoding="utf-8") as handle:
        for idx, record in enumerate(rows, start=1):
            root = Path(record.get("workspace") or "")
            query = str((record.get("search") or {}).get("query") or "")
            targets = base.positive_targets(record)
            if not root.is_dir() or not query or not targets:
                continue
            candidate_files = base.collect_candidate_files(root, query, candidate_limit)
            snippets = base.build_snippets(root, candidate_files)
            snippets = graph_mem.cap_snippets(snippets, query, max_snippets)
            if not snippets:
                continue
            usable += 1
            candidate_hit += int(any(target["path"] in candidate_files for target in targets))
            row = {"record_index": idx, "instance_id": record.get("instance_id"), "query": query, "targets": targets, "variants": {}}
            for name, scorer in VARIANTS.items():
                start = time.perf_counter()
                scores = scorer(snippets, query)
                timings[name] += time.perf_counter() - start
                hits = base.rank_route(snippets, scores, 5)
                metrics = hit_metrics(hits, targets)
                for key, value in metrics.items():
                    counts[name][key] += int(value)
                row["variants"][name] = {"metrics": metrics, "hits": [hit["uri"] for hit in hits[:5]]}
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    table = []
    for name in VARIANTS:
        table.append({
            "variant": name,
            "top1": round(counts[name]["top1"] / usable, 4),
            "top3": round(counts[name]["top3"] / usable, 4),
            "top5": round(counts[name]["top5"] / usable, 4),
            "top1_count": counts[name]["top1"],
            "top3_count": counts[name]["top3"],
            "top5_count": counts[name]["top5"],
            "avg_score_time_sec": round(timings[name] / usable, 6),
        })
    table.sort(key=lambda item: (item["top5"], item["top3"], item["top1"]), reverse=True)
    metrics = {
        "dataset": str(dataset),
        "predictions": str(pred_path),
        "experiment_scope": "canonical_bm25_route_variants",
        "usable_records": usable,
        "candidate_limit": candidate_limit,
        "max_snippets_per_record": max_snippets,
        "candidate_recall": round(candidate_hit / usable, 4),
        "variants": table,
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n")
    lines = [
        "# BM25 Route Variants",
        "",
        "Metric:",
        "",
        "```text",
        "grep candidate pool -> BM25-family route ranks snippets independently -> top1/top3/top5 hit",
        "```",
        "",
        f"- usable_records: `{usable}`",
        f"- candidate_limit: `{candidate_limit}`",
        f"- max_snippets_per_record: `{max_snippets}`",
        f"- candidate_recall: `{metrics['candidate_recall']:.4f}`",
        "",
        "| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_score_time_sec |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in table:
        lines.append(
            f"| {item['variant']} | {item['top1']:.4f} | {item['top3']:.4f} | {item['top5']:.4f} | "
            f"{item['top1_count']} | {item['top3_count']} | {item['top5_count']} | {item['avg_score_time_sec']:.6f} |"
        )
    (out_dir / "bm25_route_variants.md").write_text("\n".join(lines) + "\n")
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(ROOT / "artifacts" / "legacy-search-dataset" / "search_targets.jsonl"))
    parser.add_argument("--out-dir", default=str(ROOT / "artifacts" / "bm25-route-exp"))
    parser.add_argument("--candidate-limit", type=int, default=80)
    parser.add_argument("--max-snippets", type=int, default=500)
    args = parser.parse_args()
    metrics = evaluate(Path(args.dataset), Path(args.out_dir), args.candidate_limit, args.max_snippets)
    print(json.dumps(metrics["variants"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
