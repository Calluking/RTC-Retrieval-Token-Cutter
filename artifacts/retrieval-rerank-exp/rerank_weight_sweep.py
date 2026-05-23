#!/usr/bin/env python3
"""Weight sweep for final reranking over improved four-route top5 union."""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import sys
import time
from pathlib import Path
from typing import Any


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
emb = import_module("embedding_variants_eval", ROOT / "artifacts" / "retrieval-embedding-exp" / "embedding_variants_eval.py")
bm25_route = import_module("bm25_route_variants", ROOT / "artifacts" / "bm25-route-exp" / "bm25_route_variants.py")
sym = import_module("symbol_variants_eval", ROOT / "artifacts" / "retrieval-symbol-exp" / "symbol_variants_eval.py")
ctags_route = import_module("ctags_route_variants", ROOT / "artifacts" / "ctags-route-exp" / "ctags_route_variants.py")
graph_mem = import_module("graph_memory_variants_eval", ROOT / "artifacts" / "retrieval-graph-memory-exp" / "graph_memory_variants_eval.py")
rerank = import_module("final_rerank_experiments", ROOT / "artifacts" / "retrieval-rerank-exp" / "final_rerank_experiments.py")


ROUTES = ("embedding", "bm25", "ctags", "graph")


def hit_metrics(hits: list[dict[str, Any]], targets: list[dict[str, Any]]) -> dict[str, bool]:
    return {
        "top1": any(base.hit_target(hit, targets, False) for hit in hits[:1]),
        "top3": any(base.hit_target(hit, targets, False) for hit in hits[:3]),
        "top5": any(base.hit_target(hit, targets, False) for hit in hits[:5]),
    }


def counts_row(name: str, counts: dict[str, int], usable: int) -> dict[str, Any]:
    return {
        "reranker": name,
        "top1": round(counts["top1"] / usable, 4) if usable else 0.0,
        "top3": round(counts["top3"] / usable, 4) if usable else 0.0,
        "top5": round(counts["top5"] / usable, 4) if usable else 0.0,
        "top1_count": counts["top1"],
        "top3_count": counts["top3"],
        "top5_count": counts["top5"],
    }


def weight_grid() -> list[dict[str, float]]:
    weights: list[dict[str, float]] = []
    for vals in itertools.product((0.0, 0.5, 1.0, 1.5, 2.0), repeat=4):
        total = sum(vals)
        if total <= 0:
            continue
        weights.append({route: val / total for route, val in zip(ROUTES, vals)})
    return weights


def label(prefix: str, weights: dict[str, float]) -> str:
    parts = ",".join(f"{route[:1]}={weights[route]:.2f}" for route in ROUTES)
    return f"{prefix}({parts})"


def build_cases(dataset: Path, candidate_limit: int, max_snippets: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    cases: list[dict[str, Any]] = []
    candidate_hit = 0
    candidate_time = 0.0
    route_time = 0.0
    for idx, record in enumerate(records, start=1):
        root = Path(record.get("workspace") or "")
        query = str((record.get("search") or {}).get("query") or "")
        targets = base.positive_targets(record)
        if not root.is_dir() or not query or not targets:
            continue
        start = time.perf_counter()
        candidate_files = base.collect_candidate_files(root, query, candidate_limit)
        snippets = base.build_snippets(root, candidate_files)
        snippets = graph_mem.cap_snippets(snippets, query, max_snippets)
        graph = graph_mem.build_memory_graph(snippets)
        candidate_time += time.perf_counter() - start
        if not snippets:
            continue
        route_start = time.perf_counter()
        score_maps = {
            "embedding": emb.query_with_scope(snippets, record, query),
            "bm25": bm25_route.bm25f_symbol_heavy(snippets, query),
            "ctags": sym.exact_ctags(snippets, query),
            "graph": graph_mem.l1_relation_rrf(graph, query),
        }
        aux_maps = {
            "path_scope": ctags_route.path_scoped_symbol(snippets, record, query),
            "late": emb.late_interaction(snippets, record, query),
        }
        route_time += time.perf_counter() - route_start
        route_hits = {route: rerank.rank_uris(scores, 5) for route, scores in score_maps.items()}
        candidate_uris = set(uri for uris in route_hits.values() for uri in uris)
        cases.append({
            "record_index": idx,
            "targets": targets,
            "snippets_by_uri": {snippet.uri: snippet for snippet in snippets},
            "score_maps": score_maps,
            "aux_maps": aux_maps,
            "route_hits": route_hits,
            "candidate_uris": candidate_uris,
        })
        candidate_hit += int(any(target["path"] in candidate_files for target in targets))
    meta = {
        "usable_records": len(cases),
        "candidate_recall": round(candidate_hit / len(cases), 4) if cases else 0.0,
        "avg_candidate_and_graph_build_sec": round(candidate_time / len(cases), 6) if cases else 0.0,
        "avg_route_scoring_sec": round(route_time / len(cases), 6) if cases else 0.0,
    }
    return cases, meta


def evaluate_scores(cases: list[dict[str, Any]], name: str, scores_fn) -> dict[str, Any]:
    counts = {"top1": 0, "top3": 0, "top5": 0}
    for case in cases:
        scores = scores_fn(case)
        hits = rerank.rank_hits(case["snippets_by_uri"], scores, 5)
        metrics = hit_metrics(hits, case["targets"])
        for key, value in metrics.items():
            counts[key] += int(value)
    return counts_row(name, counts, len(cases))


def evaluate(dataset: Path, out_dir: Path, candidate_limit: int, max_snippets: int) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cases, meta = build_cases(dataset, candidate_limit, max_snippets)
    rows: list[dict[str, Any]] = []

    for weights in weight_grid():
        rows.append(evaluate_scores(
            cases,
            label("rrf", weights),
            lambda case, weights=weights: rerank.rrf(case["candidate_uris"], case["route_hits"], weights),
        ))
        rows.append(evaluate_scores(
            cases,
            label("sum", weights),
            lambda case, weights=weights: rerank.weighted_sum(case["candidate_uris"], case["score_maps"], weights),
        ))

    base_rrf = lambda case: rerank.rrf(case["candidate_uris"], case["route_hits"])
    base_max = lambda case: rerank.max_route(case["candidate_uris"], case["score_maps"])
    for alpha in (0.1, 0.2, 0.3, 0.4, 0.5):
        rows.append(evaluate_scores(
            cases,
            f"rrf_equal_plus_max_alpha={alpha:.1f}",
            lambda case, alpha=alpha: rerank.add_scores((base_rrf(case), 1.0 - alpha), (base_max(case), alpha)),
        ))
        rows.append(evaluate_scores(
            cases,
            f"rrf_equal_plus_path_alpha={alpha:.1f}",
            lambda case, alpha=alpha: rerank.add_scores(
                (base_rrf(case), 1.0 - alpha),
                ({uri: case["aux_maps"]["path_scope"].get(uri, 0.0) for uri in case["candidate_uris"]}, alpha),
            ),
        ))

    rows.sort(key=lambda item: (item["top5"], item["top3"], item["top1"]), reverse=True)
    metrics = {
        "dataset": str(dataset),
        "experiment_scope": "route_top5_union_final_rerank_weight_sweep",
        "candidate_limit": candidate_limit,
        "max_snippets_per_record": max_snippets,
        **meta,
        "variants_tested": len(rows),
        "top_results": rows[:30],
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(metrics, out_dir / "rerank_weight_sweep.md")
    return metrics


def write_markdown(metrics: dict[str, Any], path: Path) -> None:
    lines = [
        "# Rerank Weight Sweep",
        "",
        "Metric:",
        "",
        "```text",
        "grep candidate pool -> improved 4 route top5 union -> final reranker -> top1/top3/top5 hit",
        "```",
        "",
        f"- usable_records: `{metrics['usable_records']}`",
        f"- candidate_limit: `{metrics['candidate_limit']}`",
        f"- max_snippets_per_record: `{metrics['max_snippets_per_record']}`",
        f"- candidate_recall: `{metrics['candidate_recall']:.4f}`",
        f"- variants_tested: `{metrics['variants_tested']}`",
        "",
        "## Top Results",
        "",
        "| reranker | top1 | top3 | top5 | top1_count | top3_count | top5_count |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in metrics["top_results"]:
        lines.append(
            f"| `{row['reranker']}` | {row['top1']:.4f} | {row['top3']:.4f} | {row['top5']:.4f} | "
            f"{row['top1_count']} | {row['top3_count']} | {row['top5_count']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(ROOT / "artifacts" / "legacy-search-dataset" / "search_targets.jsonl"))
    parser.add_argument("--out-dir", default=str(ROOT / "artifacts" / "retrieval-rerank-exp" / "weight_sweep"))
    parser.add_argument("--candidate-limit", type=int, default=80)
    parser.add_argument("--max-snippets", type=int, default=500)
    args = parser.parse_args()
    metrics = evaluate(Path(args.dataset), Path(args.out_dir), args.candidate_limit, args.max_snippets)
    print(json.dumps(metrics["top_results"][:15], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
