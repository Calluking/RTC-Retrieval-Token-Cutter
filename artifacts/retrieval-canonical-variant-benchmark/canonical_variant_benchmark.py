#!/usr/bin/env python3
"""Canonical route-variant benchmark.

Metric:
  full grep candidate pool -> one route variant ranks snippets -> top1/3/5 hit

This is the route optimization metric. It intentionally does not rerank the
existing four-route top5 union.
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
sym = import_module("symbol_variants_eval", ROOT / "artifacts" / "retrieval-symbol-exp" / "symbol_variants_eval.py")
graph_mem = import_module("graph_memory_variants_eval", ROOT / "artifacts" / "retrieval-graph-memory-exp" / "graph_memory_variants_eval.py")


VariantFn = Callable[[list[Any], dict[str, Any], str, Any | None], dict[str, float]]


def variant_groups() -> dict[str, dict[str, VariantFn]]:
    return {
        "embedding": {
            "baseline_embedding_proxy": lambda snippets, record, query, graph: emb.baseline(snippets, record, query),
            "query_plus_issue": lambda snippets, record, query, graph: emb.query_with_issue(snippets, record, query),
            "query_plus_legacy_scope": lambda snippets, record, query, graph: emb.query_with_scope(snippets, record, query),
            "field_weighted_embedding": lambda snippets, record, query, graph: emb.field_weighted(snippets, record, query),
            "pseudo_relevance_feedback": lambda snippets, record, query, graph: emb.prf_expand(snippets, record, query),
            "late_interaction_proxy": lambda snippets, record, query, graph: emb.late_interaction(snippets, record, query),
        },
        "bm25": {
            "bm25_default": lambda snippets, record, query, graph: bm25v.bm25_default(snippets, query),
            "bm25_tuned_short_code": lambda snippets, record, query, graph: bm25v.bm25_tuned_short_code(snippets, query),
            "bm25_plus": lambda snippets, record, query, graph: bm25v.bm25_plus(snippets, query),
            "bm25_l": lambda snippets, record, query, graph: bm25v.bm25_l(snippets, query),
            "bm25f_code_fields": lambda snippets, record, query, graph: bm25v.bm25f_code_fields(snippets, query),
            "dirichlet_lm": lambda snippets, record, query, graph: bm25v.dirichlet_lm(snippets, query),
        },
        "symbol": {
            "ctags_default": lambda snippets, record, query, graph: sym.exact_ctags(snippets, query),
            "ctags_plus_subtoken": lambda snippets, record, query, graph: sym.ctags_plus_subtoken(snippets, query),
            "ctags_plus_fuzzy": lambda snippets, record, query, graph: sym.ctags_plus_fuzzy(snippets, query),
            "all_symbol_features": lambda snippets, record, query, graph: sym.all_symbol_features(snippets, query),
            "identifier_subtoken": lambda snippets, record, query, graph: sym.identifier_subtoken(snippets, query),
            "fuzzy_symbol": lambda snippets, record, query, graph: sym.fuzzy_symbol(snippets, query),
            "acronym_abbrev": lambda snippets, record, query, graph: sym.acronym_abbrev(snippets, query),
            "kind_aware_symbol": lambda snippets, record, query, graph: sym.kind_aware_symbol(snippets, query),
            "symbol_graph_neighbor": lambda snippets, record, query, graph: sym.symbol_graph_neighbor(snippets, query),
        },
        "graph_memory": {
            "l1_relation_1hop": lambda snippets, record, query, graph: graph_mem.l1_relation_1hop(graph, query),
            "l1_relation_2hop_decay": lambda snippets, record, query, graph: graph_mem.l1_relation_2hop_decay(graph, query),
            "l1_query_gated_walk": lambda snippets, record, query, graph: graph_mem.l1_query_gated_walk(graph, query),
            "l1_relation_pagerank": lambda snippets, record, query, graph: graph_mem.l1_relation_pagerank(graph, query),
            "l1_relation_rrf": lambda snippets, record, query, graph: graph_mem.l1_relation_rrf(graph, query),
        },
    }


def empty_counts() -> dict[str, int]:
    return {"top1": 0, "top3": 0, "top5": 0}


def hit_metrics(hits: list[dict[str, Any]], targets: list[dict[str, Any]]) -> dict[str, bool]:
    return {
        "top1": any(base.hit_target(hit, targets, False) for hit in hits[:1]),
        "top3": any(base.hit_target(hit, targets, False) for hit in hits[:3]),
        "top5": any(base.hit_target(hit, targets, False) for hit in hits[:5]),
    }


def rank_snippets(snippets: list[Any], scores: dict[str, float], limit: int) -> list[Any]:
    by_uri = {snippet.uri: snippet for snippet in snippets}
    ranked = [
        (score, by_uri[uri])
        for uri, score in scores.items()
        if score > 0 and uri in by_uri
    ]
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [snippet for _, snippet in ranked[:limit]]


def snippet_hit_metrics(hits: list[Any], targets: list[dict[str, Any]]) -> dict[str, bool]:
    as_dicts = [base.snippet_dict(snippet, 1.0) for snippet in hits[:5]]
    return hit_metrics(as_dicts, targets)


def row(name: str, counts: dict[str, int], usable: int, total_time: float) -> dict[str, Any]:
    return {
        "variant": name,
        "top1": round(counts["top1"] / usable, 4) if usable else 0.0,
        "top3": round(counts["top3"] / usable, 4) if usable else 0.0,
        "top5": round(counts["top5"] / usable, 4) if usable else 0.0,
        "top1_count": counts["top1"],
        "top3_count": counts["top3"],
        "top5_count": counts["top5"],
        "avg_score_time_sec": round(total_time / usable, 6) if usable else 0.0,
    }


def evaluate(
    dataset: Path,
    out_dir: Path,
    candidate_limit: int,
    max_snippets: int,
    top_k: int,
    only_groups: set[str] | None = None,
) -> dict[str, Any]:
    records = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    groups = variant_groups()
    if only_groups:
        groups = {name: variants for name, variants in groups.items() if name in only_groups}
    out_dir.mkdir(parents=True, exist_ok=True)

    counts = {
        group: {variant: empty_counts() for variant in variants}
        for group, variants in groups.items()
    }
    timings = {
        group: defaultdict(float)
        for group in groups
    }
    usable = 0
    candidate_hit = 0
    candidate_time_total = 0.0
    graph_time_total = 0.0
    snippet_counts: list[int] = []
    pred_path = out_dir / "canonical_variant_predictions.jsonl"
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
            candidate_time = time.perf_counter() - start
            if not snippets:
                continue
            memory_graph = None
            graph_time = 0.0
            if "graph_memory" in groups:
                graph_start = time.perf_counter()
                memory_graph = graph_mem.build_memory_graph(snippets)
                graph_time = time.perf_counter() - graph_start

            usable += 1
            candidate_time_total += candidate_time
            graph_time_total += graph_time
            snippet_counts.append(len(snippets))
            candidate_hit += int(any(target["path"] in candidate_files for target in targets))
            out_row = {
                "record_index": idx,
                "instance_id": record.get("instance_id"),
                "query": query,
                "targets": targets,
                "candidate_file_count": len(candidate_files),
                "snippet_count": len(snippets),
                "candidate_time_sec": candidate_time,
                "memory_graph_build_time_sec": graph_time,
                "groups": {},
            }
            for group, variants in groups.items():
                out_row["groups"][group] = {}
                for name, scorer in variants.items():
                    score_start = time.perf_counter()
                    scores = scorer(snippets, record, query, memory_graph)
                    elapsed = time.perf_counter() - score_start
                    timings[group][name] += elapsed
                    hits = rank_snippets(snippets, scores, max(top_k, 5))
                    metrics = snippet_hit_metrics(hits, targets)
                    for key, value in metrics.items():
                        counts[group][name][key] += int(value)
                    out_row["groups"][group][name] = {
                        "metrics": metrics,
                        "score_time_sec": elapsed,
                    }
            handle.write(json.dumps(out_row, ensure_ascii=False) + "\n")

    tables: dict[str, list[dict[str, Any]]] = {}
    for group, variants in groups.items():
        rows = [
            row(name, counts[group][name], usable, timings[group][name])
            for name in variants
        ]
        rows.sort(key=lambda item: (item["top5"], item["top3"], item["top1"]), reverse=True)
        tables[group] = rows

    metrics = {
        "dataset": str(dataset),
        "predictions": str(pred_path),
        "experiment_scope": "full_grep_candidate_pool_route_variant_top5",
        "usable_records": usable,
        "candidate_limit": candidate_limit,
        "max_snippets_per_record": max_snippets,
        "candidate_recall": round(candidate_hit / usable, 4) if usable else 0.0,
        "avg_snippets_per_search": round(sum(snippet_counts) / usable, 2) if usable else 0.0,
        "avg_candidate_build_sec": round(candidate_time_total / usable, 6) if usable else 0.0,
        "avg_memory_graph_build_sec": round(graph_time_total / usable, 6) if usable else 0.0,
        "tables": tables,
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(metrics, out_dir / "canonical_variant_benchmark.md")
    return metrics


def table_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_score_time_sec |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in rows:
        lines.append(
            f"| {item['variant']} | {item['top1']:.4f} | {item['top3']:.4f} | {item['top5']:.4f} | "
            f"{item['top1_count']} | {item['top3_count']} | {item['top5_count']} | {item['avg_score_time_sec']:.6f} |"
        )
    return lines


def write_markdown(metrics: dict[str, Any], path: Path) -> None:
    lines = [
        "# Canonical Variant Benchmark",
        "",
        "Metric:",
        "",
        "```text",
        "full grep candidate pool -> route variant ranks independently -> top1/top3/top5 hit",
        "```",
        "",
        "## Settings",
        "",
        f"- usable_records: {metrics['usable_records']}",
        f"- candidate_limit: {metrics['candidate_limit']}",
        f"- max_snippets_per_record: {metrics['max_snippets_per_record']}",
        f"- candidate_recall: {metrics['candidate_recall']:.4f}",
        f"- avg_snippets_per_search: {metrics['avg_snippets_per_search']:.2f}",
        f"- avg_candidate_build_sec: {metrics['avg_candidate_build_sec']:.6f}",
        f"- avg_memory_graph_build_sec: {metrics['avg_memory_graph_build_sec']:.6f}",
    ]
    for group in ("embedding", "bm25", "symbol", "graph_memory"):
        if group in metrics["tables"]:
            lines.extend(["", f"## {group}", "", *table_lines(metrics["tables"][group])])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(ROOT / "artifacts" / "legacy-search-dataset" / "search_targets.jsonl"))
    parser.add_argument("--out-dir", default=str(ROOT / "artifacts" / "retrieval-canonical-variant-benchmark"))
    parser.add_argument("--candidate-limit", type=int, default=80)
    parser.add_argument("--max-snippets", type=int, default=500)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--groups", default="", help="Comma-separated subset: embedding,bm25,symbol,graph_memory")
    args = parser.parse_args()
    groups = {part.strip() for part in args.groups.split(",") if part.strip()} or None
    metrics = evaluate(Path(args.dataset), Path(args.out_dir), args.candidate_limit, args.max_snippets, args.top_k, groups)
    print(json.dumps(metrics["tables"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
