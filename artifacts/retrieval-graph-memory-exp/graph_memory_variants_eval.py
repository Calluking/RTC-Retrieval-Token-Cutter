#!/usr/bin/env python3
"""Evaluate L1-memory relation traversal variants for code retrieval.

Unlike graph_variants_eval.py, this script does not reconstruct a graph from
only the existing top5 union. For each query it rebuilds the grep candidate
snippet pool, resolves L1-style graph relations to concrete snippet locators,
then scores snippets by traversing those stored relations.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
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


CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
DEF_RE = re.compile(r"^\s*(?:async\s+def|def)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.M)
CLASS_BASE_RE = re.compile(r"^\s*class\s+[A-Za-z_][A-Za-z0-9_]*\s*\(([^)]*)\)\s*:", re.M)
CALL_SKIP = {
    "if", "for", "while", "with", "return", "class", "def", "assert",
    "raise", "except", "print", "len", "str", "int", "float", "bool",
    "list", "dict", "set", "tuple", "super",
}


@dataclass
class Relation:
    source_uri: str
    target_uri: str
    type: str
    name: str
    target_path: str
    target_start_line: int
    target_end_line: int
    target_symbol: str


@dataclass
class MemoryGraph:
    snippets: list[Any]
    by_uri: dict[str, Any]
    out_edges: dict[str, list[Relation]]
    in_edges: dict[str, list[Relation]]


def leaf(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    return text.rsplit(".", 1)[-1]


def relation_values(snippet: Any) -> dict[str, list[str]]:
    """Extract the relation names that are stored in L1 graph fields.

    The artifact snippets do not persist the exact production L1 file, so this
    recreates the same relation-name fields from AST snippets: calls, extends,
    and contains. Traversal only uses relations after they are resolved to
    concrete target snippets, mirroring graph.resolved_relations.
    """
    graph = {
        "calls": [],
        "extends": [],
        "contains": [],
    }
    text = snippet.text
    if snippet.kind in {"function", "async_function", "type"}:
        graph["calls"].extend(name for name in CALL_RE.findall(text) if name not in CALL_SKIP)
    if snippet.kind == "type":
        for bases in CLASS_BASE_RE.findall(snippet.signature + "\n" + text):
            for raw in bases.split(","):
                name = raw.strip().split(".")[-1]
                if name:
                    graph["extends"].append(name)
        graph["contains"].extend(name for name in DEF_RE.findall(text) if name != snippet.symbol)
    return {key: list(dict.fromkeys(values)) for key, values in graph.items()}


def cap_snippets(snippets: list[Any], query: str, max_snippets: int) -> list[Any]:
    if max_snippets <= 0 or len(snippets) <= max_snippets:
        return snippets
    ctags = base.ctags_scores(snippets, query)
    bm25 = base.bm25_scores(snippets, query)
    ctags_n = normalize(ctags)
    bm25_n = normalize(bm25)
    scored = []
    for snippet in snippets:
        score = 0.65 * ctags_n.get(snippet.uri, 0.0) + 0.35 * bm25_n.get(snippet.uri, 0.0)
        scored.append((score, snippet))
    scored.sort(key=lambda item: (item[0], -item[1].start_line), reverse=True)
    return [snippet for _, snippet in scored[:max_snippets]]


def build_memory_graph(snippets: list[Any]) -> MemoryGraph:
    by_uri = {snippet.uri: snippet for snippet in snippets}
    symbol_index: dict[str, list[Any]] = defaultdict(list)
    for snippet in snippets:
        for value in {snippet.symbol, snippet.signature.split("(", 1)[0].replace("def ", "").replace("class ", "").strip()}:
            key = leaf(value)
            if key:
                symbol_index[key].append(snippet)

    out_edges: dict[str, list[Relation]] = defaultdict(list)
    in_edges: dict[str, list[Relation]] = defaultdict(list)
    seen: set[tuple[str, str, str, str]] = set()
    for snippet in snippets:
        for rel_type, names in relation_values(snippet).items():
            for name in names:
                key = leaf(name)
                if not key:
                    continue
                for target in symbol_index.get(key, []):
                    if target.uri == snippet.uri:
                        continue
                    dedupe = (snippet.uri, target.uri, rel_type, name)
                    if dedupe in seen:
                        continue
                    seen.add(dedupe)
                    rel = Relation(
                        source_uri=snippet.uri,
                        target_uri=target.uri,
                        type=rel_type,
                        name=name,
                        target_path=target.rel,
                        target_start_line=target.start_line,
                        target_end_line=target.end_line,
                        target_symbol=target.symbol,
                    )
                    out_edges[snippet.uri].append(rel)
                    in_edges[target.uri].append(rel)
    return MemoryGraph(snippets, by_uri, dict(out_edges), dict(in_edges))


def snippet_text(snippet: Any) -> str:
    return " ".join([snippet.rel, snippet.symbol, snippet.signature, snippet.text])


def query_terms(query: str) -> list[str]:
    return base.extract_query_terms(query)


def anchor_ctags(graph: MemoryGraph, query: str) -> dict[str, float]:
    return base.ctags_scores(graph.snippets, query)


def anchor_text(graph: MemoryGraph, query: str) -> dict[str, float]:
    q_terms = query_terms(query)
    scores = dict(anchor_ctags(graph, query))
    for snippet in graph.snippets:
        text_l = snippet_text(snippet).lower()
        overlap = sum(1 for term in q_terms if term in text_l)
        if overlap:
            scores[snippet.uri] = max(scores.get(snippet.uri, 0.0), overlap * 0.75)
    return scores


def normalize(scores: dict[str, float]) -> dict[str, float]:
    return base.normalize(scores)


def relation_neighbors(graph: MemoryGraph, uri: str, *, reverse: bool) -> list[tuple[str, Relation, bool]]:
    out: list[tuple[str, Relation, bool]] = [(rel.target_uri, rel, False) for rel in graph.out_edges.get(uri, [])]
    if reverse:
        out.extend((rel.source_uri, rel, True) for rel in graph.in_edges.get(uri, []))
    return out


def traverse(
    graph: MemoryGraph,
    seeds: dict[str, float],
    *,
    weights: dict[str, float],
    reverse: bool,
    hops: int,
    decay: float,
    seed_keep: float = 1.0,
    query: str = "",
    gated: bool = False,
) -> dict[str, float]:
    terms = set(query_terms(query))
    scores = {uri: score * seed_keep for uri, score in seeds.items()}
    frontier = dict(seeds)
    for depth in range(1, hops + 1):
        nxt: dict[str, float] = {}
        for uri, score in frontier.items():
            for neighbor_uri, rel, is_reverse in relation_neighbors(graph, uri, reverse=reverse):
                rel_weight = weights.get(rel.type, 0.0)
                if rel_weight <= 0:
                    continue
                direction_weight = 0.72 if is_reverse else 1.0
                target = graph.by_uri.get(neighbor_uri)
                if not target:
                    continue
                gate = 1.0
                if gated and terms:
                    text_l = snippet_text(target).lower()
                    gate = 1.0 if any(term in text_l for term in terms) else 0.25
                gain = score * (decay ** depth) * rel_weight * direction_weight * gate
                if gain <= 0:
                    continue
                nxt[neighbor_uri] = max(nxt.get(neighbor_uri, 0.0), gain)
                scores[neighbor_uri] = max(scores.get(neighbor_uri, 0.0), gain)
        frontier = nxt
        if not frontier:
            break
    return scores


def l1_relation_1hop(graph: MemoryGraph, query: str) -> dict[str, float]:
    """Query anchors, then one hop over resolved L1 relations."""
    return traverse(
        graph,
        anchor_ctags(graph, query),
        weights={"calls": 0.95, "extends": 0.9, "contains": 0.75},
        reverse=True,
        hops=1,
        decay=0.7,
        query=query,
    )


def l1_relation_2hop_decay(graph: MemoryGraph, query: str) -> dict[str, float]:
    """Two-hop relation memory walk with stronger decay."""
    return traverse(
        graph,
        anchor_ctags(graph, query),
        weights={"calls": 0.9, "extends": 0.85, "contains": 0.65},
        reverse=True,
        hops=2,
        decay=0.52,
        query=query,
    )


def l1_query_gated_walk(graph: MemoryGraph, query: str) -> dict[str, float]:
    """Only trust relation expansion when the reached node still matches query evidence."""
    return traverse(
        graph,
        anchor_text(graph, query),
        weights={"calls": 0.85, "extends": 0.8, "contains": 0.6},
        reverse=True,
        hops=2,
        decay=0.6,
        query=query,
        gated=True,
    )


def l1_relation_pagerank(graph: MemoryGraph, query: str) -> dict[str, float]:
    """Personalized PageRank over resolved L1 relations, seeded by query anchors."""
    seeds = normalize(anchor_text(graph, query))
    if not seeds:
        return {}
    uris = list(graph.by_uri)
    scores = {uri: seeds.get(uri, 0.0) for uri in uris}
    alpha = 0.35
    weights = {"calls": 1.0, "extends": 0.95, "contains": 0.75}
    for _ in range(14):
        nxt = {uri: alpha * seeds.get(uri, 0.0) for uri in uris}
        for uri, value in scores.items():
            edges = graph.out_edges.get(uri, [])
            total = sum(weights.get(rel.type, 0.0) for rel in edges)
            if total <= 0:
                continue
            for rel in edges:
                w = weights.get(rel.type, 0.0)
                if w > 0:
                    nxt[rel.target_uri] += (1.0 - alpha) * value * w / total
        scores = nxt
    return {uri: score for uri, score in scores.items() if score > 0}


def l1_relation_rrf(graph: MemoryGraph, query: str) -> dict[str, float]:
    """Reciprocal-rank fusion of anchor rank and relation-walk rank."""
    anchor = anchor_text(graph, query)
    walk = l1_relation_1hop(graph, query)
    ppr = l1_relation_pagerank(graph, query)
    maps = [anchor, walk, ppr]
    out: dict[str, float] = defaultdict(float)
    for scores in maps:
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        for rank, (uri, _) in enumerate(ranked, start=1):
            out[uri] += 1.0 / (60.0 + rank)
    return dict(out)


VARIANTS: dict[str, Callable[[MemoryGraph, str], dict[str, float]]] = {
    "l1_relation_1hop": l1_relation_1hop,
    "l1_relation_2hop_decay": l1_relation_2hop_decay,
    "l1_query_gated_walk": l1_query_gated_walk,
    "l1_relation_pagerank": l1_relation_pagerank,
    "l1_relation_rrf": l1_relation_rrf,
}


def relation_stats(graph: MemoryGraph) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for edges in graph.out_edges.values():
        for rel in edges:
            counts[rel.type] += 1
    counts["total"] = sum(v for k, v in counts.items() if k != "total")
    return dict(counts)


def hit_metrics(hits: list[dict[str, Any]], targets: list[dict[str, Any]]) -> dict[str, bool]:
    return {
        "top1": any(base.hit_target(hit, targets, False) for hit in hits[:1]),
        "top3": any(base.hit_target(hit, targets, False) for hit in hits[:3]),
        "top5": any(base.hit_target(hit, targets, False) for hit in hits[:5]),
    }


def evaluate(dataset: Path, out_dir: Path, candidate_limit: int, top_k: int, max_snippets: int) -> dict[str, Any]:
    records = [json.loads(line) for line in dataset.read_text().splitlines() if line.strip()]
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {name: {"top1": 0, "top3": 0, "top5": 0} for name in VARIANTS}
    usable = 0
    candidate_hit = 0
    relation_total = 0
    relation_records = 0
    pred_path = out_dir / "graph_memory_variant_predictions.jsonl"
    with pred_path.open("w", encoding="utf-8") as handle:
        for idx, record in enumerate(records, start=1):
            root = Path(record.get("workspace") or "")
            query = str((record.get("search") or {}).get("query") or "")
            targets = base.positive_targets(record)
            if not root.is_dir() or not query or not targets:
                continue
            candidate_files = base.collect_candidate_files(root, query, candidate_limit)
            snippets = base.build_snippets(root, candidate_files)
            snippets = cap_snippets(snippets, query, max_snippets)
            if not snippets:
                continue
            graph = build_memory_graph(snippets)
            stats = relation_stats(graph)
            relation_total += stats.get("total", 0)
            relation_records += int(stats.get("total", 0) > 0)
            usable += 1
            candidate_hit += int(any(target["path"] in candidate_files for target in targets))
            row = {
                "record_index": idx,
                "instance_id": record.get("instance_id"),
                "query": query,
                "targets": targets,
                "candidate_file_count": len(candidate_files),
                "snippet_count": len(snippets),
                "relation_stats": stats,
                "variants": {},
            }
            for name, scorer in VARIANTS.items():
                scores = scorer(graph, query)
                hits = base.rank_route(snippets, scores, max(top_k, 5))
                metrics = hit_metrics(hits, targets)
                for key, value in metrics.items():
                    counts[name][key] += int(value)
                row["variants"][name] = {"metrics": metrics, "hits": hits[:5]}
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    table = []
    for name, route_counts in counts.items():
        table.append({
            "variant": name,
            "top1": round(route_counts["top1"] / usable, 4) if usable else 0.0,
            "top3": round(route_counts["top3"] / usable, 4) if usable else 0.0,
            "top5": round(route_counts["top5"] / usable, 4) if usable else 0.0,
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
        "max_snippets_per_record": max_snippets,
        "candidate_recall": round(candidate_hit / usable, 4) if usable else 0.0,
        "records_with_resolved_l1_relations": relation_records,
        "avg_resolved_l1_relations": round(relation_total / usable, 2) if usable else 0.0,
        "experiment_scope": "grep_candidate_pool_then_resolved_l1_relation_memory_traversal",
        "variants": table,
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n")
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
    parser.add_argument("--out-dir", default=str(ROOT / "artifacts" / "retrieval-graph-memory-exp"))
    parser.add_argument("--candidate-limit", type=int, default=80)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--max-snippets", type=int, default=800)
    args = parser.parse_args()
    metrics = evaluate(Path(args.dataset), Path(args.out_dir), args.candidate_limit, args.top_k, args.max_snippets)
    print(json.dumps(metrics["variants"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
