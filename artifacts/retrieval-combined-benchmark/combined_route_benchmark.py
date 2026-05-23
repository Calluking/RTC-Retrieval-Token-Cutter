#!/usr/bin/env python3
"""Compare original RTC-style routes with updated route variants.

This benchmark uses the same grep candidate generation for both systems, then
compares:

original: embedding_proxy, bm25_default, ctags_default, graph_proxy
updated:  late_interaction_proxy, bm25_tuned_short_code, ctags_default,
          l1_relation_rrf

Fusion weights are kept identical so route quality changes are not mixed with
weight tuning.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from collections import defaultdict
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
emb = import_module("embedding_variants_eval", ROOT / "artifacts" / "retrieval-embedding-exp" / "embedding_variants_eval.py")
bm25v = import_module("bm25_variants_eval", ROOT / "artifacts" / "retrieval-bm25-exp" / "bm25_variants_eval.py")
graph_mem = import_module("graph_memory_variants_eval", ROOT / "artifacts" / "retrieval-graph-memory-exp" / "graph_memory_variants_eval.py")


WEIGHTS = {
    "embedding": 0.45,
    "bm25": 0.25,
    "ctags": 0.15,
    "graph": 0.15,
}


RouteFn = Callable[[list[Any], dict[str, Any], str, Any | None], dict[str, float]]


def original_routes() -> dict[str, RouteFn]:
    return {
        "embedding": lambda snippets, record, query, graph: base.embedding_proxy_scores(snippets, query),
        "bm25": lambda snippets, record, query, graph: base.bm25_scores(snippets, query),
        "ctags": lambda snippets, record, query, graph: base.ctags_scores(snippets, query),
        "graph": lambda snippets, record, query, graph: base.graph_proxy_scores(snippets, query),
    }


def updated_routes() -> dict[str, RouteFn]:
    return {
        "embedding": lambda snippets, record, query, graph: emb.late_interaction(snippets, record, query),
        "bm25": lambda snippets, record, query, graph: bm25v.bm25_tuned_short_code(snippets, query),
        "ctags": lambda snippets, record, query, graph: base.ctags_scores(snippets, query),
        "graph": lambda snippets, record, query, graph: graph_mem.l1_relation_rrf(graph, query) if graph else {},
    }


def empty_counts() -> dict[str, int]:
    return {"top1": 0, "top3": 0, "top5": 0}


def update_counts(counts: dict[str, int], hits: list[dict[str, Any]], targets: list[dict[str, Any]]) -> None:
    counts["top1"] += int(any(base.hit_target(hit, targets, False) for hit in hits[:1]))
    counts["top3"] += int(any(base.hit_target(hit, targets, False) for hit in hits[:3]))
    counts["top5"] += int(any(base.hit_target(hit, targets, False) for hit in hits[:5]))


def row_from_counts(name: str, counts: dict[str, int], usable: int) -> dict[str, Any]:
    return {
        "name": name,
        "top1": round(counts["top1"] / usable, 4) if usable else 0.0,
        "top3": round(counts["top3"] / usable, 4) if usable else 0.0,
        "top5": round(counts["top5"] / usable, 4) if usable else 0.0,
        "top1_count": counts["top1"],
        "top3_count": counts["top3"],
        "top5_count": counts["top5"],
    }


def fused_hits(
    snippets: list[Any],
    route_scores: dict[str, dict[str, float]],
    route_hits: dict[str, list[dict[str, Any]]],
    top_k: int,
) -> list[dict[str, Any]]:
    by_uri = {snippet.uri: snippet for snippet in snippets}
    normed = {route: base.normalize(scores) for route, scores in route_scores.items()}
    candidate_uris: set[str] = set()
    for hits in route_hits.values():
        candidate_uris.update(str(hit["uri"]) for hit in hits[:5])

    ranked: list[tuple[float, Any, dict[str, float]]] = []
    for uri in candidate_uris:
        snippet = by_uri.get(uri)
        if not snippet:
            continue
        parts = {route: normed.get(route, {}).get(uri, 0.0) for route in WEIGHTS}
        score = sum(WEIGHTS[route] * parts.get(route, 0.0) for route in WEIGHTS)
        ranked.append((score, snippet, parts))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [base.snippet_dict(snippet, score, parts) for score, snippet, parts in ranked[:top_k]]


def evaluate_system(
    *,
    name: str,
    routes: dict[str, RouteFn],
    snippets: list[Any],
    record: dict[str, Any],
    query: str,
    targets: list[dict[str, Any]],
    graph: Any | None,
    top_k: int,
) -> tuple[dict[str, dict[str, int]], dict[str, float], dict[str, list[dict[str, Any]]]]:
    counts = {route: empty_counts() for route in list(routes) + ["overall"]}
    timings: dict[str, float] = {}
    score_maps: dict[str, dict[str, float]] = {}
    route_hits: dict[str, list[dict[str, Any]]] = {}
    for route, fn in routes.items():
        start = time.perf_counter()
        scores = fn(snippets, record, query, graph)
        timings[route] = time.perf_counter() - start
        score_maps[route] = scores
        hits = base.rank_route(snippets, scores, max(top_k, 5))
        route_hits[route] = hits
        update_counts(counts[route], hits, targets)

    start = time.perf_counter()
    overall_hits = fused_hits(snippets, score_maps, route_hits, top_k)
    timings["overall_rerank"] = time.perf_counter() - start
    route_hits["overall"] = overall_hits
    update_counts(counts["overall"], overall_hits, targets)
    return counts, timings, route_hits


def evaluate(dataset: Path, out_dir: Path, candidate_limit: int, max_snippets: int, top_k: int) -> dict[str, Any]:
    rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    out_dir.mkdir(parents=True, exist_ok=True)

    system_defs = {
        "original": original_routes(),
        "updated": updated_routes(),
    }
    aggregate_counts = {
        system: {route: empty_counts() for route in ["embedding", "bm25", "ctags", "graph", "overall"]}
        for system in system_defs
    }
    aggregate_timings: dict[str, dict[str, float]] = {
        system: defaultdict(float) for system in system_defs
    }
    aggregate_total_time = {system: 0.0 for system in system_defs}
    aggregate_candidate_time = 0.0
    aggregate_memory_graph_time = 0.0

    usable = 0
    candidate_hit = 0
    snippet_counts: list[int] = []
    pred_path = out_dir / "combined_predictions.jsonl"
    with pred_path.open("w", encoding="utf-8") as handle:
        for idx, record in enumerate(rows, start=1):
            root = Path(record.get("workspace") or "")
            query = str((record.get("search") or {}).get("query") or "")
            targets = base.positive_targets(record)
            if not root.is_dir() or not query or not targets:
                continue

            search_start = time.perf_counter()
            candidate_files = base.collect_candidate_files(root, query, candidate_limit)
            snippets = base.build_snippets(root, candidate_files)
            snippets = graph_mem.cap_snippets(snippets, query, max_snippets)
            graph_start = time.perf_counter()
            memory_graph = graph_mem.build_memory_graph(snippets)
            graph_build_time = time.perf_counter() - graph_start
            candidate_time = time.perf_counter() - search_start - graph_build_time
            if not snippets:
                continue

            usable += 1
            aggregate_candidate_time += candidate_time
            aggregate_memory_graph_time += graph_build_time
            snippet_counts.append(len(snippets))
            candidate_hit += int(any(target["path"] in candidate_files for target in targets))
            row = {
                "record_index": idx,
                "instance_id": record.get("instance_id"),
                "query": query,
                "targets": targets,
                "candidate_file_count": len(candidate_files),
                "snippet_count": len(snippets),
                "candidate_time_sec": candidate_time,
                "memory_graph_build_time_sec": graph_build_time,
                "systems": {},
            }
            for system, routes in system_defs.items():
                system_start = time.perf_counter()
                counts, timings, hits = evaluate_system(
                    name=system,
                    routes=routes,
                    snippets=snippets,
                    record=record,
                    query=query,
                    targets=targets,
                    graph=memory_graph,
                    top_k=top_k,
                )
                system_route_time = time.perf_counter() - system_start
                total = candidate_time + system_route_time
                if system == "updated":
                    total += graph_build_time
                aggregate_total_time[system] += total
                for route, route_counts in counts.items():
                    for metric, value in route_counts.items():
                        aggregate_counts[system][route][metric] += value
                for key, value in timings.items():
                    aggregate_timings[system][key] += value
                row["systems"][system] = {
                    "timings_sec": timings,
                    "hits_by_route": {route: route_hits[:5] for route, route_hits in hits.items()},
                }
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    comparison: dict[str, list[dict[str, Any]]] = {}
    timing_table: list[dict[str, Any]] = []
    for system in system_defs:
        comparison[system] = [
            row_from_counts(route, aggregate_counts[system][route], usable)
            for route in ["embedding", "bm25", "ctags", "graph", "overall"]
        ]
        timing_row = {
            "system": system,
            "avg_search_total_sec": round(aggregate_total_time[system] / usable, 6) if usable else 0.0,
            "avg_candidate_build_sec": round(aggregate_candidate_time / usable, 6) if usable else 0.0,
        }
        if system == "updated":
            timing_row["avg_memory_graph_build_sec"] = round(aggregate_memory_graph_time / usable, 6) if usable else 0.0
        else:
            timing_row["avg_memory_graph_build_sec"] = 0.0
        for key, value in sorted(aggregate_timings[system].items()):
            timing_row[f"avg_{key}_sec"] = round(value / usable, 6) if usable else 0.0
        timing_table.append(timing_row)

    metrics = {
        "dataset": str(dataset),
        "predictions": str(pred_path),
        "usable_records": usable,
        "candidate_limit": candidate_limit,
        "max_snippets_per_record": max_snippets,
        "top_k": top_k,
        "candidate_recall": round(candidate_hit / usable, 4) if usable else 0.0,
        "avg_snippets_per_search": round(sum(snippet_counts) / usable, 2) if usable else 0.0,
        "fusion_weights": WEIGHTS,
        "original_routes": {
            "embedding": "embedding_proxy",
            "bm25": "bm25_default",
            "ctags": "ctags_default",
            "graph": "graph_proxy",
        },
        "updated_routes": {
            "embedding": "late_interaction_proxy",
            "bm25": "bm25_tuned_short_code",
            "ctags": "ctags_default",
            "graph": "l1_relation_rrf",
        },
        "comparison": comparison,
        "timing": timing_table,
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(metrics, out_dir / "combined_route_benchmark.md")
    return metrics


def markdown_table(rows: list[dict[str, Any]], name_key: str = "name") -> list[str]:
    lines = [
        "| route | top1 | top3 | top5 | top1_count | top3_count | top5_count |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row[name_key]} | {row['top1']:.4f} | {row['top3']:.4f} | {row['top5']:.4f} | "
            f"{row['top1_count']} | {row['top3_count']} | {row['top5_count']} |"
        )
    return lines


def write_markdown(metrics: dict[str, Any], path: Path) -> None:
    lines = [
        "# Combined Route Benchmark",
        "",
        "## Settings",
        "",
        f"- usable_records: {metrics['usable_records']}",
        f"- candidate_limit: {metrics['candidate_limit']}",
        f"- max_snippets_per_record: {metrics['max_snippets_per_record']}",
        f"- candidate_recall: {metrics['candidate_recall']:.4f}",
        f"- avg_snippets_per_search: {metrics['avg_snippets_per_search']:.2f}",
        f"- fusion_weights: `{json.dumps(metrics['fusion_weights'])}`",
        "",
        "Scope note: this is a full grep-candidate recompute benchmark. It is",
        "not the same as the earlier per-route experiments that reranked only the",
        "existing four-route top5 union, so those metrics should not be expected",
        "to match exactly.",
        "",
        "Route mapping:",
        "",
        f"- original: `{json.dumps(metrics['original_routes'])}`",
        f"- updated: `{json.dumps(metrics['updated_routes'])}`",
        "",
        "## Original Routes",
        "",
        *markdown_table(metrics["comparison"]["original"]),
        "",
        "## Updated Routes",
        "",
        *markdown_table(metrics["comparison"]["updated"]),
        "",
        "## Side-By-Side Deltas",
        "",
        "| route | original_top1 | updated_top1 | delta_top1 | original_top3 | updated_top3 | delta_top3 | original_top5 | updated_top5 | delta_top5 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    original = {row["name"]: row for row in metrics["comparison"]["original"]}
    updated = {row["name"]: row for row in metrics["comparison"]["updated"]}
    for route in ["embedding", "bm25", "ctags", "graph", "overall"]:
        old1, new1 = original[route]["top1"], updated[route]["top1"]
        old3, new3 = original[route]["top3"], updated[route]["top3"]
        old5, new5 = original[route]["top5"], updated[route]["top5"]
        lines.append(
            f"| {route} | {old1:.4f} | {new1:.4f} | {new1 - old1:+.4f} | "
            f"{old3:.4f} | {new3:.4f} | {new3 - old3:+.4f} | "
            f"{old5:.4f} | {new5:.4f} | {new5 - old5:+.4f} |"
        )
    lines.extend([
        "",
        "## Timing",
        "",
        "| system | avg_search_total_sec | avg_candidate_build_sec | avg_memory_graph_build_sec | avg_embedding_sec | avg_bm25_sec | avg_ctags_sec | avg_graph_sec | avg_overall_rerank_sec |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in metrics["timing"]:
        lines.append(
            f"| {row['system']} | {row.get('avg_search_total_sec', 0.0):.6f} | "
            f"{row.get('avg_candidate_build_sec', 0.0):.6f} | "
            f"{row.get('avg_memory_graph_build_sec', 0.0):.6f} | "
            f"{row.get('avg_embedding_sec', 0.0):.6f} | {row.get('avg_bm25_sec', 0.0):.6f} | "
            f"{row.get('avg_ctags_sec', 0.0):.6f} | {row.get('avg_graph_sec', 0.0):.6f} | "
            f"{row.get('avg_overall_rerank_sec', 0.0):.6f} |"
        )
    lines.extend([
        "",
        "Timing note: `avg_search_total_sec` includes candidate/snippet building.",
        "For the updated system it also includes L1 memory graph construction.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(ROOT / "artifacts" / "legacy-search-dataset" / "search_targets.jsonl"))
    parser.add_argument("--out-dir", default=str(ROOT / "artifacts" / "retrieval-combined-benchmark"))
    parser.add_argument("--candidate-limit", type=int, default=80)
    parser.add_argument("--max-snippets", type=int, default=500)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    metrics = evaluate(Path(args.dataset), Path(args.out_dir), args.candidate_limit, args.max_snippets, args.top_k)
    print(json.dumps({
        "comparison": metrics["comparison"],
        "timing": metrics["timing"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
