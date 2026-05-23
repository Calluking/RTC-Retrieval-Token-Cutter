#!/usr/bin/env python3
"""Graph-route reranking variants over existing RTC predictions.

These variants are artifact-side proxies. They build a lightweight typed graph
from the snippets already present in the four-route top5 union, then test
different query-to-graph scoring policies without changing production code.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
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
IMPORT_RE = re.compile(r"^\s*(?:from\s+([A-Za-z_][\w.]*)\s+import|import\s+([A-Za-z_][\w.]*))", re.M)
CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(([^)]*)\))?:", re.M)
DEF_RE = re.compile(r"^\s*(?:async\s+def|def)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.M)
CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|[_\W]+")
CALL_SKIP = {
    "if", "for", "while", "with", "return", "class", "def", "assert",
    "raise", "except", "print", "len", "str", "int", "float", "bool",
    "list", "dict", "set", "tuple", "super",
}


@dataclass
class Graph:
    snippets: list[Any]
    by_uri: dict[str, Any]
    edges: dict[str, list[tuple[str, str, float]]]
    rev_edges: dict[str, list[tuple[str, str, float]]]
    calls: dict[str, set[str]]
    imports: dict[str, set[str]]
    bases: dict[str, set[str]]
    tokens: dict[str, set[str]]


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


def field_tokens(snippet: Any) -> set[str]:
    return set(
        split_identifier(snippet.rel)
        + split_identifier(snippet.symbol)
        + split_identifier(snippet.signature)
        + base.tokenize(snippet.text)
    )


def extract_calls(text: str) -> set[str]:
    return {name for name in CALL_RE.findall(text) if name not in CALL_SKIP}


def extract_imports(text: str) -> set[str]:
    found: set[str] = set()
    for left, right in IMPORT_RE.findall(text):
        module = left or right
        if module:
            found.update(part.lower() for part in module.split(".") if part)
    return found


def extract_bases(signature: str, text: str) -> set[str]:
    found: set[str] = set()
    for _, bases in CLASS_RE.findall("\n".join([signature, text])):
        for item in bases.split(","):
            name = item.strip().split(".")[-1]
            if name:
                found.update(split_identifier(name))
                found.add(name.lower())
    return found


def add_edge(edges: dict[str, dict[str, dict[str, float]]], src: str, dst: str, kind: str, weight: float) -> None:
    if src == dst:
        return
    bucket = edges[src].setdefault(dst, {})
    bucket[kind] = max(bucket.get(kind, 0.0), weight)


def build_graph(snippets: list[Any]) -> Graph:
    by_uri = {snippet.uri: snippet for snippet in snippets}
    calls = {s.uri: extract_calls(s.text) for s in snippets}
    imports = {s.uri: extract_imports(s.text) for s in snippets}
    bases = {s.uri: extract_bases(s.signature, s.text) for s in snippets}
    tokens = {s.uri: field_tokens(s) for s in snippets}

    by_symbol: dict[str, list[Any]] = defaultdict(list)
    by_file: dict[str, list[Any]] = defaultdict(list)
    for snippet in snippets:
        for token in split_identifier(snippet.symbol):
            by_symbol[token].append(snippet)
        by_symbol[snippet.symbol.lower()].append(snippet)
        by_file[snippet.rel].append(snippet)

    edge_maps: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)
    for rel, file_snippets in by_file.items():
        ordered = sorted(file_snippets, key=lambda s: (s.start_line, s.end_line))
        for i, left in enumerate(ordered):
            rel_parts = set(split_identifier(rel))
            for right in ordered:
                if left.uri == right.uri:
                    continue
                if left.start_line <= right.start_line and right.end_line <= left.end_line:
                    add_edge(edge_maps, left.uri, right.uri, "contains", 1.4)
                    add_edge(edge_maps, right.uri, left.uri, "contained_by", 0.8)
            for right in ordered[max(0, i - 3): i + 4]:
                if left.uri == right.uri:
                    continue
                dist = abs(right.start_line - left.start_line)
                add_edge(edge_maps, left.uri, right.uri, "same_file_near", 1.0 / (1.0 + dist / 60.0))
            for right in ordered:
                if left.uri != right.uri and rel_parts & tokens[right.uri]:
                    add_edge(edge_maps, left.uri, right.uri, "same_package", 0.25)

    for snippet in snippets:
        uri = snippet.uri
        for called in calls[uri]:
            for target in by_symbol.get(called.lower(), []):
                add_edge(edge_maps, uri, target.uri, "calls", 1.8)
                add_edge(edge_maps, target.uri, uri, "called_by", 1.0)
        for base_name in bases[uri]:
            for target in by_symbol.get(base_name.lower(), []):
                add_edge(edge_maps, uri, target.uri, "extends", 1.7)
                add_edge(edge_maps, target.uri, uri, "extended_by", 1.0)
        for imp in imports[uri]:
            for target in snippets:
                if imp in split_identifier(target.rel) or imp in split_identifier(target.symbol):
                    add_edge(edge_maps, uri, target.uri, "imports", 1.0)
                    add_edge(edge_maps, target.uri, uri, "imported_by", 0.6)

    edges: dict[str, list[tuple[str, str, float]]] = {}
    rev_edges: dict[str, list[tuple[str, str, float]]] = defaultdict(list)
    for src, dsts in edge_maps.items():
        edges[src] = []
        for dst, kinds in dsts.items():
            for kind, weight in kinds.items():
                edges[src].append((dst, kind, weight))
                rev_edges[dst].append((src, kind, weight))
    return Graph(snippets, by_uri, edges, dict(rev_edges), calls, imports, bases, tokens)


def lexical_anchor(graph: Graph, query: str) -> dict[str, float]:
    return base.ctags_scores(graph.snippets, query)


def body_anchor(graph: Graph, query: str) -> dict[str, float]:
    terms = query_terms(query)
    scores = lexical_anchor(graph, query)
    for snippet in graph.snippets:
        tok = graph.tokens[snippet.uri]
        overlap = sum(1 for term in terms if term in tok)
        if overlap:
            scores[snippet.uri] = max(scores.get(snippet.uri, 0.0), overlap * 0.9)
    return scores


def normalize(scores: dict[str, float]) -> dict[str, float]:
    return base.normalize(scores)


def propagate(
    graph: Graph,
    seeds: dict[str, float],
    *,
    edge_weights: dict[str, float],
    decay: float,
    hops: int,
    include_reverse: bool = False,
    keep_seed_boost: float = 1.0,
) -> dict[str, float]:
    scores = {uri: value * keep_seed_boost for uri, value in seeds.items()}
    frontier = dict(seeds)
    for _ in range(hops):
        nxt: dict[str, float] = {}
        for uri, value in frontier.items():
            outgoing = list(graph.edges.get(uri, []))
            if include_reverse:
                outgoing += list(graph.rev_edges.get(uri, []))
            for dst, kind, weight in outgoing:
                kind_weight = edge_weights.get(kind, 0.0)
                if kind_weight <= 0:
                    continue
                gain = value * decay * kind_weight * weight
                if gain <= 0:
                    continue
                nxt[dst] = max(nxt.get(dst, 0.0), gain)
                scores[dst] = max(scores.get(dst, 0.0), gain)
        frontier = nxt
        if not frontier:
            break
    return scores


def current_graph_proxy(graph: Graph, query: str) -> dict[str, float]:
    return base.graph_proxy_scores(graph.snippets, query)


def containment_expansion(graph: Graph, query: str) -> dict[str, float]:
    return propagate(graph, lexical_anchor(graph, query), edge_weights={
        "contains": 1.0, "contained_by": 0.8, "same_file_near": 0.25,
    }, decay=0.65, hops=2, include_reverse=True, keep_seed_boost=1.0)


def callgraph_expansion(graph: Graph, query: str) -> dict[str, float]:
    return propagate(graph, lexical_anchor(graph, query), edge_weights={
        "calls": 1.0, "called_by": 0.7, "contains": 0.25, "contained_by": 0.2,
    }, decay=0.72, hops=2, include_reverse=True, keep_seed_boost=1.0)


def import_expansion(graph: Graph, query: str) -> dict[str, float]:
    return propagate(graph, body_anchor(graph, query), edge_weights={
        "imports": 1.0, "imported_by": 0.65, "same_package": 0.35,
    }, decay=0.7, hops=2, include_reverse=True, keep_seed_boost=1.0)


def inheritance_expansion(graph: Graph, query: str) -> dict[str, float]:
    return propagate(graph, lexical_anchor(graph, query), edge_weights={
        "extends": 1.0, "extended_by": 0.8, "contains": 0.3, "contained_by": 0.3,
    }, decay=0.75, hops=2, include_reverse=True, keep_seed_boost=1.0)


def typed_weighted_bfs(graph: Graph, query: str) -> dict[str, float]:
    return propagate(graph, body_anchor(graph, query), edge_weights={
        "calls": 0.95, "called_by": 0.7, "extends": 0.9, "extended_by": 0.7,
        "imports": 0.55, "imported_by": 0.35, "contains": 0.75,
        "contained_by": 0.55, "same_file_near": 0.25,
    }, decay=0.62, hops=2, include_reverse=True, keep_seed_boost=1.0)


def query_gated_bfs(graph: Graph, query: str) -> dict[str, float]:
    terms = set(query_terms(query))
    seeds = body_anchor(graph, query)
    base_scores = dict(seeds)
    frontier = dict(seeds)
    for _ in range(2):
        nxt: dict[str, float] = {}
        for uri, value in frontier.items():
            for dst, kind, weight in graph.edges.get(uri, []) + graph.rev_edges.get(uri, []):
                gate = 1.0 if graph.tokens[dst] & terms else 0.35
                kind_weight = {
                    "calls": 0.9, "called_by": 0.65, "contains": 0.75,
                    "contained_by": 0.55, "extends": 0.8, "extended_by": 0.65,
                    "imports": 0.45, "same_file_near": 0.2,
                }.get(kind, 0.1)
                gain = value * 0.65 * kind_weight * weight * gate
                if gain > 0:
                    nxt[dst] = max(nxt.get(dst, 0.0), gain)
                    base_scores[dst] = max(base_scores.get(dst, 0.0), gain)
        frontier = nxt
    return base_scores


def personalized_pagerank(graph: Graph, query: str) -> dict[str, float]:
    seeds = normalize(body_anchor(graph, query))
    if not seeds:
        return {}
    scores = {uri: seeds.get(uri, 0.0) for uri in graph.by_uri}
    alpha = 0.35
    edge_weights = {
        "calls": 1.0, "called_by": 0.75, "contains": 0.8, "contained_by": 0.55,
        "extends": 0.9, "extended_by": 0.7, "imports": 0.55, "imported_by": 0.35,
        "same_file_near": 0.25, "same_package": 0.1,
    }
    for _ in range(12):
        nxt = {uri: alpha * seeds.get(uri, 0.0) for uri in graph.by_uri}
        for uri, value in scores.items():
            outgoing = [(dst, kind, w) for dst, kind, w in graph.edges.get(uri, []) if edge_weights.get(kind, 0.0) > 0]
            total = sum(edge_weights[kind] * weight for _, kind, weight in outgoing)
            if total <= 0:
                continue
            for dst, kind, weight in outgoing:
                nxt[dst] += (1.0 - alpha) * value * edge_weights[kind] * weight / total
        scores = nxt
    return {uri: score for uri, score in scores.items() if score > 0}


def spreading_activation(graph: Graph, query: str) -> dict[str, float]:
    seeds = normalize(body_anchor(graph, query))
    active = dict(seeds)
    scores = dict(seeds)
    for _ in range(3):
        nxt: dict[str, float] = {}
        for uri, value in active.items():
            if value < 0.05:
                continue
            for dst, kind, weight in graph.edges.get(uri, []) + graph.rev_edges.get(uri, []):
                gain = value * weight * {
                    "calls": 0.5, "called_by": 0.45, "contains": 0.55,
                    "contained_by": 0.4, "extends": 0.5, "extended_by": 0.4,
                    "imports": 0.3, "same_file_near": 0.2,
                }.get(kind, 0.05)
                if gain >= 0.03:
                    nxt[dst] = max(nxt.get(dst, 0.0), gain)
                    scores[dst] = scores.get(dst, 0.0) + gain
        active = nxt
    return scores


def graph_kernel_overlap(graph: Graph, query: str) -> dict[str, float]:
    terms = set(query_terms(query))
    seed_scores = body_anchor(graph, query)
    scores: dict[str, float] = {}
    for snippet in graph.snippets:
        uri = snippet.uri
        neighborhood = set(graph.tokens[uri])
        relation_bonus = Counter()
        for dst, kind, _ in graph.edges.get(uri, []) + graph.rev_edges.get(uri, []):
            neighborhood.update(graph.tokens.get(dst, set()))
            relation_bonus[kind] += 1
        overlap = len(terms & neighborhood)
        if overlap or uri in seed_scores:
            scores[uri] = seed_scores.get(uri, 0.0) + overlap * 0.8
            scores[uri] += 0.15 * (relation_bonus["calls"] + relation_bonus["called_by"])
            scores[uri] += 0.1 * (relation_bonus["contains"] + relation_bonus["contained_by"])
    return scores


def path_package_graph(graph: Graph, query: str) -> dict[str, float]:
    terms = set(query_terms(query))
    scores = lexical_anchor(graph, query)
    by_file_score: dict[str, float] = defaultdict(float)
    for snippet in graph.snippets:
        path_parts = set(split_identifier(snippet.rel))
        hit = len(path_parts & terms)
        if hit:
            by_file_score[snippet.rel] = max(by_file_score[snippet.rel], float(hit))
    for snippet in graph.snippets:
        if snippet.rel in by_file_score:
            scores[snippet.uri] = max(scores.get(snippet.uri, 0.0), by_file_score[snippet.rel] * 0.9)
    return propagate(graph, scores, edge_weights={
        "same_package": 1.0, "same_file_near": 0.55, "contains": 0.45, "contained_by": 0.35,
    }, decay=0.55, hops=2, include_reverse=False, keep_seed_boost=1.0)


def hybrid_symbol_graph(graph: Graph, query: str) -> dict[str, float]:
    maps = [
        (normalize(base.ctags_scores(graph.snippets, query)), 0.45),
        (normalize(typed_weighted_bfs(graph, query)), 0.3),
        (normalize(graph_kernel_overlap(graph, query)), 0.15),
        (normalize(personalized_pagerank(graph, query)), 0.1),
    ]
    out: dict[str, float] = {}
    for scores, weight in maps:
        for uri, score in scores.items():
            out[uri] = out.get(uri, 0.0) + weight * score
    return out


VARIANTS: dict[str, Callable[[Graph, str], dict[str, float]]] = {
    "graph_current_proxy": current_graph_proxy,
    "containment_expansion": containment_expansion,
    "callgraph_expansion": callgraph_expansion,
    "import_expansion": import_expansion,
    "inheritance_expansion": inheritance_expansion,
    "typed_weighted_bfs": typed_weighted_bfs,
    "query_gated_bfs": query_gated_bfs,
    "personalized_pagerank": personalized_pagerank,
    "spreading_activation": spreading_activation,
    "graph_kernel_overlap": graph_kernel_overlap,
    "path_package_graph": path_package_graph,
    "hybrid_symbol_graph": hybrid_symbol_graph,
}


def evaluate(dataset: Path, predictions: Path, out_dir: Path, top_k: int) -> dict[str, Any]:
    records = [json.loads(line) for line in dataset.read_text().splitlines() if line.strip()]
    pred_rows = [json.loads(line) for line in predictions.read_text().splitlines() if line.strip()]
    by_index = {int(row["record_index"]): row for row in pred_rows}
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {name: {"top1": 0, "top3": 0, "top5": 0} for name in VARIANTS}
    usable = 0
    candidate_union_hit = 0
    pred_path = out_dir / "graph_variant_union_predictions.jsonl"
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
            graph = build_graph(snippets)
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
                hits = base.rank_route(snippets, scorer(graph, query), max(top_k, 5))
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
    parser.add_argument("--out-dir", default=str(ROOT / "artifacts" / "retrieval-graph-exp"))
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    metrics = evaluate(Path(args.dataset), Path(args.predictions), Path(args.out_dir), args.top_k)
    print(json.dumps(metrics["variants"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
