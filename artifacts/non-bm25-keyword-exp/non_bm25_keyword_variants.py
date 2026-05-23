#!/usr/bin/env python3
"""Non-BM25 keyword/frequency route variants under the canonical metric."""

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
bm25_route = import_module("bm25_route_variants", ROOT / "artifacts" / "bm25-route-exp" / "bm25_route_variants.py")
graph_mem = import_module("graph_memory_variants_eval", ROOT / "artifacts" / "retrieval-graph-memory-exp" / "graph_memory_variants_eval.py")


def q_terms(query: str) -> list[str]:
    return [t for t in base.tokenize(query) if t not in base.STOP_TERMS]


def fields(snippet: Any) -> dict[str, list[str]]:
    return {
        "symbol": base.tokenize(snippet.symbol),
        "signature": base.tokenize(snippet.signature),
        "path": base.tokenize(snippet.rel),
        "body": base.tokenize(snippet.text),
        "all": base.tokenize(" ".join([snippet.rel, snippet.symbol, snippet.signature, snippet.text])),
    }


def corpus(snippets: list[Any], field: str) -> tuple[list[list[str]], Counter[str], Counter[str], int, float]:
    docs = [fields(s)[field] for s in snippets]
    dfs: Counter[str] = Counter()
    cf: Counter[str] = Counter()
    for doc in docs:
        cf.update(doc)
        for term in set(doc):
            dfs[term] += 1
    total_len = sum(len(doc) for doc in docs)
    avgdl = total_len / max(1, len(docs))
    return docs, dfs, cf, total_len, avgdl


def tfidf_fielded(snippets: list[Any], query: str) -> dict[str, float]:
    """Classic vector-space TF-IDF cosine with code-field weights."""
    terms = q_terms(query)
    field_weights = {"symbol": 4.0, "signature": 2.5, "path": 1.4, "body": 0.45}
    field_data = {name: corpus(snippets, name) for name in field_weights}
    n = len(snippets)
    q_tf = Counter(terms)
    scores: dict[str, float] = {}
    for i, snippet in enumerate(snippets):
        dot = doc_norm = q_norm = 0.0
        for field_name, weight in field_weights.items():
            docs, dfs, _cf, _total, _avgdl = field_data[field_name]
            tf = Counter(docs[i])
            for term, qf in q_tf.items():
                df = dfs.get(term, 0)
                if not df:
                    continue
                idf = math.log((n + 1.0) / (df + 1.0)) + 1.0
                qv = (1.0 + math.log(qf)) * idf
                dv = (1.0 + math.log(tf[term])) * idf * weight if tf.get(term, 0) else 0.0
                dot += qv * dv
                q_norm += qv * qv
            for term, freq in tf.items():
                df = dfs.get(term, 0)
                idf = math.log((n + 1.0) / (df + 1.0)) + 1.0
                dv = (1.0 + math.log(freq)) * idf * weight
                doc_norm += dv * dv
        if dot > 0 and doc_norm > 0 and q_norm > 0:
            scores[snippet.uri] = dot / math.sqrt(doc_norm * q_norm)
    return scores


def lm_dirichlet_fielded(snippets: list[Any], query: str, mu: float = 900.0) -> dict[str, float]:
    """Query likelihood with Dirichlet smoothing over a weighted field mixture."""
    terms = q_terms(query)
    field_weights = {"symbol": 3.2, "signature": 2.2, "path": 1.3, "body": 0.5}
    data = {name: corpus(snippets, name) for name in field_weights}
    scores: dict[str, float] = {}
    for i, snippet in enumerate(snippets):
        score = 0.0
        matched = False
        for term in terms:
            prob = 0.0
            for field_name, weight in field_weights.items():
                docs, _dfs, cf, total, _avgdl = data[field_name]
                doc = docs[i]
                tf = Counter(doc)
                pc = cf.get(term, 0) / max(total, 1)
                field_prob = (tf.get(term, 0) + mu * pc) / (len(doc) + mu)
                prob += weight * field_prob
                matched = matched or tf.get(term, 0) > 0
            denom = sum(field_weights.values())
            score += math.log(max(prob / denom, 1e-12))
        if matched:
            scores[snippet.uri] = math.exp(score / max(1, len(terms)))
    return scores


def lm_jelinek_mercer_fielded(snippets: list[Any], query: str, lam: float = 0.18) -> dict[str, float]:
    """Query likelihood with Jelinek-Mercer interpolation."""
    terms = q_terms(query)
    field_weights = {"symbol": 3.0, "signature": 2.0, "path": 1.2, "body": 0.6}
    data = {name: corpus(snippets, name) for name in field_weights}
    scores: dict[str, float] = {}
    for i, snippet in enumerate(snippets):
        score = 0.0
        matched = False
        for term in terms:
            prob = 0.0
            for field_name, weight in field_weights.items():
                docs, _dfs, cf, total, _avgdl = data[field_name]
                doc = docs[i]
                tf = Counter(doc)
                mle = tf.get(term, 0) / max(len(doc), 1)
                pc = cf.get(term, 0) / max(total, 1)
                prob += weight * ((1.0 - lam) * mle + lam * pc)
                matched = matched or tf.get(term, 0) > 0
            score += math.log(max(prob / sum(field_weights.values()), 1e-12))
        if matched:
            scores[snippet.uri] = math.exp(score / max(1, len(terms)))
    return scores


def dfr_pl2_fielded(snippets: list[Any], query: str) -> dict[str, float]:
    """Approximate DFR PL2 with code-field weighting."""
    terms = q_terms(query)
    field_weights = {"symbol": 4.0, "signature": 2.5, "path": 1.2, "body": 0.5}
    data = {name: corpus(snippets, name) for name in field_weights}
    scores: dict[str, float] = defaultdict(float)
    c = 1.0
    for field_name, weight in field_weights.items():
        docs, _dfs, cf, total, avgdl = data[field_name]
        for i, snippet in enumerate(snippets):
            tf = Counter(docs[i])
            dl = len(docs[i])
            for term in terms:
                f = tf.get(term, 0)
                if f <= 0:
                    continue
                tfn = f * math.log2(1.0 + c * avgdl / max(dl, 1))
                lamb = cf.get(term, 0) / max(len(snippets), 1)
                if tfn <= 0 or lamb <= 0:
                    continue
                # PL2-style contribution, simplified for stable positive ranking.
                part = (tfn * math.log2(tfn / lamb) + (lamb + 1.0 / (12.0 * tfn) - tfn) * math.log2(math.e) + 0.5 * math.log2(2.0 * math.pi * tfn))
                scores[snippet.uri] += weight * max(part / (tfn + 1.0), 0.0)
    return dict(scores)


def field_rrf_tfidf(snippets: list[Any], query: str) -> dict[str, float]:
    """RRF over separate TF-IDF rankings for path/symbol/signature/body."""
    field_weights = {"symbol": 1.0, "signature": 1.0, "path": 1.0, "body": 1.0}
    out: dict[str, float] = defaultdict(float)
    for field_name in field_weights:
        fake_snippets = snippets
        # Reuse TF-IDF logic by temporarily scoring one field.
        terms = q_terms(query)
        docs, dfs, _cf, _total, _avgdl = corpus(fake_snippets, field_name)
        n = len(snippets)
        scores: dict[str, float] = {}
        for i, snippet in enumerate(snippets):
            tf = Counter(docs[i])
            score = 0.0
            for term in terms:
                if tf.get(term, 0):
                    score += (1.0 + math.log(tf[term])) * (math.log((n + 1.0) / (dfs[term] + 1.0)) + 1.0)
            if score > 0:
                scores[snippet.uri] = score
        for rank, (uri, _score) in enumerate(sorted(scores.items(), key=lambda item: item[1], reverse=True), start=1):
            out[uri] += 1.0 / (60.0 + rank)
    return dict(out)


VARIANTS = {
    "tfidf_fielded": tfidf_fielded,
    "lm_dirichlet_fielded": lm_dirichlet_fielded,
    "lm_jelinek_mercer_fielded": lm_jelinek_mercer_fielded,
    "dfr_pl2_fielded": dfr_pl2_fielded,
    "field_rrf_tfidf": field_rrf_tfidf,
    "bm25f_symbol_heavy_baseline": bm25_route.bm25f_symbol_heavy,
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
    pred_path = out_dir / "non_bm25_keyword_predictions.jsonl"
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
        "experiment_scope": "canonical_non_bm25_keyword_variants",
        "usable_records": usable,
        "candidate_limit": candidate_limit,
        "max_snippets_per_record": max_snippets,
        "candidate_recall": round(candidate_hit / usable, 4),
        "variants": table,
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n")
    lines = [
        "# Non-BM25 Keyword Variants",
        "",
        "Metric:",
        "",
        "```text",
        "grep candidate pool -> non-BM25 keyword route ranks snippets independently -> top1/top3/top5 hit",
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
    (out_dir / "non_bm25_keyword_variants.md").write_text("\n".join(lines) + "\n")
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(ROOT / "artifacts" / "legacy-search-dataset" / "search_targets.jsonl"))
    parser.add_argument("--out-dir", default=str(ROOT / "artifacts" / "non-bm25-keyword-exp"))
    parser.add_argument("--candidate-limit", type=int, default=80)
    parser.add_argument("--max-snippets", type=int, default=500)
    args = parser.parse_args()
    metrics = evaluate(Path(args.dataset), Path(args.out_dir), args.candidate_limit, args.max_snippets)
    print(json.dumps(metrics["variants"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
