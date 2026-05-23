#!/usr/bin/env python3
"""Final reranking experiments over candidates from the four improved routes.

Pipeline:
  1. Build grep candidate pool.
  2. Score snippets with improved route candidates:
     embedding=query_plus_legacy_scope, bm25=bm25f_symbol_heavy,
     symbol=ctags_default, graph=l1_relation_rrf.
  3. Union each route's topK candidates.
  4. Try final reranking formulas over that union.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from collections import defaultdict
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
bm25v = import_module("bm25_variants_eval", ROOT / "artifacts" / "retrieval-bm25-exp" / "bm25_variants_eval.py")
bm25_route = import_module("bm25_route_variants", ROOT / "artifacts" / "bm25-route-exp" / "bm25_route_variants.py")
sym = import_module("symbol_variants_eval", ROOT / "artifacts" / "retrieval-symbol-exp" / "symbol_variants_eval.py")
ctags_route = import_module("ctags_route_variants", ROOT / "artifacts" / "ctags-route-exp" / "ctags_route_variants.py")
graph_mem = import_module("graph_memory_variants_eval", ROOT / "artifacts" / "retrieval-graph-memory-exp" / "graph_memory_variants_eval.py")


ROUTE_WEIGHTS_ORIGINAL = {"embedding": 0.45, "bm25": 0.25, "ctags": 0.15, "graph": 0.15}
ROUTE_WEIGHTS_BALANCED = {"embedding": 0.25, "bm25": 0.25, "ctags": 0.25, "graph": 0.25}
ROUTE_WEIGHTS_STRUCTURAL = {"embedding": 0.20, "bm25": 0.25, "ctags": 0.25, "graph": 0.30}
ROUTE_WEIGHTS_ROUTE_TOP5 = {"embedding": 0.18, "bm25": 0.30, "ctags": 0.24, "graph": 0.28}


def rank_uris(scores: dict[str, float], limit: int) -> list[str]:
    return [uri for uri, score in sorted(scores.items(), key=lambda item: item[1], reverse=True) if score > 0][:limit]


def route_rank_maps(route_hits: dict[str, list[str]]) -> dict[str, dict[str, int]]:
    return {
        route: {uri: rank for rank, uri in enumerate(uris, start=1)}
        for route, uris in route_hits.items()
    }


def normalize(scores: dict[str, float]) -> dict[str, float]:
    return base.normalize(scores)


def weighted_sum(
    candidate_uris: set[str],
    score_maps: dict[str, dict[str, float]],
    weights: dict[str, float],
) -> dict[str, float]:
    normed = {route: normalize(scores) for route, scores in score_maps.items()}
    out: dict[str, float] = {}
    for uri in candidate_uris:
        out[uri] = sum(weights.get(route, 0.0) * normed.get(route, {}).get(uri, 0.0) for route in weights)
    return out


def rrf(
    candidate_uris: set[str],
    route_hits: dict[str, list[str]],
    weights: dict[str, float] | None = None,
    k: float = 60.0,
) -> dict[str, float]:
    ranks = route_rank_maps(route_hits)
    out = {uri: 0.0 for uri in candidate_uris}
    for route, route_ranks in ranks.items():
        weight = 1.0 if weights is None else weights.get(route, 0.0)
        for uri, rank in route_ranks.items():
            if uri in out:
                out[uri] += weight / (k + rank)
    return out


def max_route(candidate_uris: set[str], score_maps: dict[str, dict[str, float]]) -> dict[str, float]:
    normed = {route: normalize(scores) for route, scores in score_maps.items()}
    return {
        uri: max((scores.get(uri, 0.0) for scores in normed.values()), default=0.0)
        for uri in candidate_uris
    }


def route_consensus(candidate_uris: set[str], route_hits: dict[str, list[str]]) -> dict[str, float]:
    ranks = route_rank_maps(route_hits)
    out: dict[str, float] = {}
    for uri in candidate_uris:
        present = [rank_map[uri] for rank_map in ranks.values() if uri in rank_map]
        if not present:
            continue
        out[uri] = len(present) * 2.0 + sum(1.0 / rank for rank in present)
    return out


def add_scores(*weighted_maps: tuple[dict[str, float], float]) -> dict[str, float]:
    out: dict[str, float] = defaultdict(float)
    for scores, weight in weighted_maps:
        normed = normalize(scores)
        for uri, score in normed.items():
            out[uri] += weight * score
    return dict(out)


def rank_hits(snippets_by_uri: dict[str, Any], scores: dict[str, float], limit: int) -> list[dict[str, Any]]:
    ranked = [
        (score, snippets_by_uri[uri])
        for uri, score in scores.items()
        if uri in snippets_by_uri and score > 0
    ]
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [base.snippet_dict(snippet, score) for score, snippet in ranked[:limit]]


def update_counts(counts: dict[str, int], hits: list[dict[str, Any]], targets: list[dict[str, Any]]) -> None:
    counts["top1"] += int(any(base.hit_target(hit, targets, False) for hit in hits[:1]))
    counts["top3"] += int(any(base.hit_target(hit, targets, False) for hit in hits[:3]))
    counts["top5"] += int(any(base.hit_target(hit, targets, False) for hit in hits[:5]))


def row(name: str, counts: dict[str, int], usable: int, total_time: float) -> dict[str, Any]:
    return {
        "reranker": name,
        "top1": round(counts["top1"] / usable, 4) if usable else 0.0,
        "top3": round(counts["top3"] / usable, 4) if usable else 0.0,
        "top5": round(counts["top5"] / usable, 4) if usable else 0.0,
        "top1_count": counts["top1"],
        "top3_count": counts["top3"],
        "top5_count": counts["top5"],
        "avg_rerank_time_sec": round(total_time / usable, 6) if usable else 0.0,
    }


def evaluate(dataset: Path, out_dir: Path, candidate_limit: int, max_snippets: int, route_top_ks: list[int]) -> dict[str, Any]:
    records = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    out_dir.mkdir(parents=True, exist_ok=True)

    reranker_names = [
        "weighted_sum_original",
        "weighted_sum_balanced",
        "weighted_sum_structural",
        "rrf_equal",
        "rrf_weighted_structural",
        "rrf_weighted_route_top5",
        "max_route_score",
        "rrf_equal_plus_max",
        "rrf_equal_plus_path_scope",
        "consensus_plus_max",
        "graph_bm25_ctags_rrf",
        "late_interaction_only",
        "bm25f_only",
        "ctags_only",
        "path_scoped_ctags_only",
        "graph_l1_rrf_only",
        "salvaged_hybrid",
    ]
    counts = {
        str(k): {name: {"top1": 0, "top3": 0, "top5": 0} for name in reranker_names}
        for k in route_top_ks
    }
    timings = {
        str(k): defaultdict(float)
        for k in route_top_ks
    }
    union_hits = {str(k): {"top1": 0, "top3": 0, "top5": 0, "union": 0} for k in route_top_ks}

    usable = 0
    candidate_hit = 0
    candidate_time_total = 0.0
    route_time_total = 0.0
    pred_path = out_dir / "final_rerank_predictions.jsonl"
    with pred_path.open("w", encoding="utf-8") as handle:
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
            candidate_time_total += time.perf_counter() - start
            if not snippets:
                continue
            usable += 1
            candidate_hit += int(any(target["path"] in candidate_files for target in targets))
            snippets_by_uri = {snippet.uri: snippet for snippet in snippets}

            route_start = time.perf_counter()
            score_maps = {
                "embedding": emb.query_with_scope(snippets, record, query),
                "bm25": bm25_route.bm25f_symbol_heavy(snippets, query),
                "ctags": sym.exact_ctags(snippets, query),
                "graph": graph_mem.l1_relation_rrf(graph, query),
            }
            route_time_total += time.perf_counter() - route_start
            max_k = max(route_top_ks)
            full_route_hits = {route: rank_uris(scores, max_k) for route, scores in score_maps.items()}
            feature_maps = {
                "late": emb.late_interaction(snippets, record, query),
                "bm25f": score_maps["bm25"],
                "ctags": score_maps["ctags"],
                "path_scoped_ctags": ctags_route.path_scoped_symbol(snippets, record, query),
                "graph": score_maps["graph"],
            }

            out_row = {
                "record_index": idx,
                "instance_id": record.get("instance_id"),
                "query": query,
                "targets": targets,
                "route_top_k": {},
            }
            for route_top_k in route_top_ks:
                key = str(route_top_k)
                route_hits = {route: uris[:route_top_k] for route, uris in full_route_hits.items()}
                candidate_uris = set(uri for uris in route_hits.values() for uri in uris)
                union_hit = any(
                    base.hit_target(base.snippet_dict(snippets_by_uri[uri], 1.0), targets, False)
                    for uri in candidate_uris
                    if uri in snippets_by_uri
                )
                union_hits[key]["union"] += int(union_hit)

                rerank_scores = {
                    "weighted_sum_original": weighted_sum(candidate_uris, score_maps, ROUTE_WEIGHTS_ORIGINAL),
                    "weighted_sum_balanced": weighted_sum(candidate_uris, score_maps, ROUTE_WEIGHTS_BALANCED),
                    "weighted_sum_structural": weighted_sum(candidate_uris, score_maps, ROUTE_WEIGHTS_STRUCTURAL),
                    "rrf_equal": rrf(candidate_uris, route_hits),
                    "rrf_weighted_structural": rrf(candidate_uris, route_hits, ROUTE_WEIGHTS_STRUCTURAL),
                    "rrf_weighted_route_top5": rrf(candidate_uris, route_hits, ROUTE_WEIGHTS_ROUTE_TOP5),
                    "max_route_score": max_route(candidate_uris, score_maps),
                    "late_interaction_only": {uri: feature_maps["late"].get(uri, 0.0) for uri in candidate_uris},
                    "bm25f_only": {uri: feature_maps["bm25f"].get(uri, 0.0) for uri in candidate_uris},
                    "ctags_only": {uri: feature_maps["ctags"].get(uri, 0.0) for uri in candidate_uris},
                    "path_scoped_ctags_only": {uri: feature_maps["path_scoped_ctags"].get(uri, 0.0) for uri in candidate_uris},
                    "graph_l1_rrf_only": {uri: feature_maps["graph"].get(uri, 0.0) for uri in candidate_uris},
                }
                rerank_scores["rrf_equal_plus_max"] = add_scores(
                    (rerank_scores["rrf_equal"], 0.70),
                    (rerank_scores["max_route_score"], 0.30),
                )
                rerank_scores["rrf_equal_plus_path_scope"] = add_scores(
                    (rerank_scores["rrf_equal"], 0.72),
                    ({uri: feature_maps["path_scoped_ctags"].get(uri, 0.0) for uri in candidate_uris}, 0.18),
                    (rerank_scores["max_route_score"], 0.10),
                )
                rerank_scores["consensus_plus_max"] = add_scores(
                    (route_consensus(candidate_uris, route_hits), 0.55),
                    (rerank_scores["max_route_score"], 0.45),
                )
                rerank_scores["graph_bm25_ctags_rrf"] = rrf(
                    candidate_uris,
                    {route: uris for route, uris in route_hits.items() if route in {"graph", "bm25", "ctags"}},
                )
                rerank_scores["salvaged_hybrid"] = add_scores(
                    (rerank_scores["rrf_equal"], 0.40),
                    (rerank_scores["max_route_score"], 0.20),
                    ({uri: feature_maps["bm25f"].get(uri, 0.0) for uri in candidate_uris}, 0.15),
                    ({uri: feature_maps["graph"].get(uri, 0.0) for uri in candidate_uris}, 0.15),
                    ({uri: feature_maps["path_scoped_ctags"].get(uri, 0.0) for uri in candidate_uris}, 0.10),
                )

                out_row["route_top_k"][key] = {"candidate_union_size": len(candidate_uris), "rerankers": {}}
                for name, scores in rerank_scores.items():
                    rerank_start = time.perf_counter()
                    hits = rank_hits(snippets_by_uri, scores, 5)
                    timings[key][name] += time.perf_counter() - rerank_start
                    update_counts(counts[key][name], hits, targets)
                    out_row["route_top_k"][key]["rerankers"][name] = {
                        "top5_uris": [hit["uri"] for hit in hits[:5]],
                    }
            handle.write(json.dumps(out_row, ensure_ascii=False) + "\n")

    tables: dict[str, list[dict[str, Any]]] = {}
    for route_top_k in route_top_ks:
        key = str(route_top_k)
        rows = [row(name, counts[key][name], usable, timings[key][name]) for name in reranker_names]
        rows.sort(key=lambda item: (item["top5"], item["top3"], item["top1"]), reverse=True)
        tables[key] = rows

    metrics = {
        "dataset": str(dataset),
        "predictions": str(pred_path),
        "experiment_scope": "improved_4_route_topK_union_final_rerank",
        "usable_records": usable,
        "candidate_limit": candidate_limit,
        "max_snippets_per_record": max_snippets,
        "route_top_ks": route_top_ks,
        "candidate_recall": round(candidate_hit / usable, 4) if usable else 0.0,
        "avg_candidate_and_graph_build_sec": round(candidate_time_total / usable, 6) if usable else 0.0,
        "avg_route_scoring_sec": round(route_time_total / usable, 6) if usable else 0.0,
        "union_recall": {
            key: round(value["union"] / usable, 4) if usable else 0.0
            for key, value in union_hits.items()
        },
        "tables": tables,
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(metrics, out_dir / "final_rerank_experiments.md")
    return metrics


def table_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| reranker | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_rerank_time_sec |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in rows:
        lines.append(
            f"| {item['reranker']} | {item['top1']:.4f} | {item['top3']:.4f} | {item['top5']:.4f} | "
            f"{item['top1_count']} | {item['top3_count']} | {item['top5_count']} | {item['avg_rerank_time_sec']:.6f} |"
        )
    return lines


def write_markdown(metrics: dict[str, Any], path: Path) -> None:
    lines = [
        "# Final Rerank Experiments",
        "",
        "Pipeline:",
        "",
        "```text",
        "grep candidate pool -> improved 4 route topK union -> final reranker -> top5",
        "```",
        "",
        "Improved routes:",
        "",
        "- embedding: `query_plus_legacy_scope`",
        "- bm25: `bm25f_symbol_heavy`",
        "- symbol: `ctags_default`",
        "- graph: `l1_relation_rrf`",
        "",
        "## Settings",
        "",
        f"- usable_records: {metrics['usable_records']}",
        f"- candidate_limit: {metrics['candidate_limit']}",
        f"- max_snippets_per_record: {metrics['max_snippets_per_record']}",
        f"- candidate_recall: {metrics['candidate_recall']:.4f}",
        f"- avg_candidate_and_graph_build_sec: {metrics['avg_candidate_and_graph_build_sec']:.6f}",
        f"- avg_route_scoring_sec: {metrics['avg_route_scoring_sec']:.6f}",
        "",
        "## Union Recall",
        "",
        "| route_top_k | union_recall |",
        "|---:|---:|",
    ]
    for key, value in metrics["union_recall"].items():
        lines.append(f"| {key} | {value:.4f} |")
    for key in [str(k) for k in metrics["route_top_ks"]]:
        lines.extend(["", f"## Route TopK = {key}", "", *table_lines(metrics["tables"][key])])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(ROOT / "artifacts" / "legacy-search-dataset" / "search_targets.jsonl"))
    parser.add_argument("--out-dir", default=str(ROOT / "artifacts" / "retrieval-rerank-exp"))
    parser.add_argument("--candidate-limit", type=int, default=80)
    parser.add_argument("--max-snippets", type=int, default=500)
    parser.add_argument("--route-top-ks", default="5,10,20")
    args = parser.parse_args()
    route_top_ks = [int(part) for part in args.route_top_ks.split(",") if part.strip()]
    metrics = evaluate(Path(args.dataset), Path(args.out_dir), args.candidate_limit, args.max_snippets, route_top_ks)
    print(json.dumps(metrics["tables"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
