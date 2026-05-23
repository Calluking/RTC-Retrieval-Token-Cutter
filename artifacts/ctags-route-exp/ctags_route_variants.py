#!/usr/bin/env python3
"""Ctags/symbol-route variants under the canonical route metric.

Metric:
  grep candidate pool -> ctags/symbol route ranks snippets independently
  -> top1/top3/top5 hit
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import sys
import time
from collections import Counter
from difflib import SequenceMatcher
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
graph_mem = import_module("graph_memory_variants_eval", ROOT / "artifacts" / "retrieval-graph-memory-exp" / "graph_memory_variants_eval.py")


CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|[_\W]+")


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
    return [term for term in base.extract_query_terms(query) if term not in base.STOP_TERMS]


def uniq(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def norm_identifier(text: str) -> str:
    return "".join(split_identifier(text))


def trigrams(text: str) -> set[str]:
    text = f"  {text.lower()}  "
    if len(text) < 3:
        return {text.strip()} if text.strip() else set()
    return {text[i:i + 3] for i in range(len(text) - 2)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def normalize(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    if hi <= lo:
        return {uri: 1.0 for uri in scores}
    return {uri: (value - lo) / (hi - lo) for uri, value in scores.items()}


def combine(*weighted: tuple[dict[str, float], float]) -> dict[str, float]:
    out: dict[str, float] = {}
    for scores, weight in weighted:
        for uri, value in normalize(scores).items():
            out[uri] = out.get(uri, 0.0) + weight * value
    return {uri: value for uri, value in out.items() if value > 0}


def infer_path_terms(record: dict[str, Any]) -> list[str]:
    search = record.get("search") or {}
    values = [
        str(search.get("path") or ""),
        str(search.get("command") or ""),
    ]
    input_obj = search.get("input")
    if isinstance(input_obj, dict):
        values.append(str(input_obj.get("path") or ""))
    raw_terms: list[str] = []
    for value in values:
        # Keep only path-ish words; absolute prefixes are too noisy.
        for part in re.split(r"[/\\\s:]+", value):
            if not part or part.startswith("-"):
                continue
            raw_terms.extend(split_identifier(part))
    return uniq([term for term in raw_terms if term not in {"home", "workspace", "grep"}])


def kind_intent(query: str) -> dict[str, float]:
    q = query.lower()
    boosts = {"type": 1.0, "function": 1.0, "async_function": 1.0, "assignment": 1.0, "code": 1.0}
    if any(term in q for term in ("class", "type", "object", "model", "exception")):
        boosts["type"] = 1.45
    if any(term in q for term in ("def", "function", "method", "call", "test_", "test ")):
        boosts["function"] = 1.4
        boosts["async_function"] = 1.4
    if any(term in q for term in ("setting", "constant", "attribute", "variable", "option", "default")):
        boosts["assignment"] = 1.35
    return boosts


def ctags_current(snippets: list[Any], record: dict[str, Any], query: str) -> dict[str, float]:
    return base.ctags_scores(snippets, query)


def exact_prefix_symbol(snippets: list[Any], record: dict[str, Any], query: str) -> dict[str, float]:
    """Declaration search: exact, prefix, then substring symbol matching."""
    terms = query_terms(query)
    q_join = "".join(terms)
    scores: dict[str, float] = {}
    for snippet in snippets:
        symbol_parts = split_identifier(snippet.symbol)
        symbol_join = "".join(symbol_parts)
        signature_l = snippet.signature.lower()
        rel_parts = split_identifier(snippet.rel)
        score = 0.0
        if q_join and q_join == symbol_join:
            score += 12.0
        elif q_join and symbol_join.startswith(q_join):
            score += 8.0
        elif terms and all(term in symbol_parts for term in terms):
            score += 6.0
        elif q_join and q_join in symbol_join:
            score += 4.0
        for term in terms:
            if term in symbol_parts:
                score += 2.0
            if term in signature_l:
                score += 0.8
            if term in rel_parts:
                score += 0.4
        if score > 0:
            scores[snippet.uri] = score
    return scores


def zoekt_like_symbol_signal(snippets: list[Any], record: dict[str, Any], query: str) -> dict[str, float]:
    """Substring/trigram code-search signal with a strong symbol boost."""
    terms = query_terms(query)
    q_join = "".join(terms)
    q_tri = trigrams(q_join)
    scores: dict[str, float] = {}
    for snippet in snippets:
        symbol_join = norm_identifier(snippet.symbol)
        sig_join = norm_identifier(snippet.signature)
        rel_join = norm_identifier(snippet.rel)
        text_l = snippet.text.lower()
        score = 0.0
        score += 5.0 * jaccard(q_tri, trigrams(symbol_join))
        score += 2.0 * jaccard(q_tri, trigrams(sig_join))
        score += 1.2 * jaccard(q_tri, trigrams(rel_join))
        for term in terms:
            if term in symbol_join:
                score += 2.2
            if term in sig_join:
                score += 0.9
            if term in rel_join:
                score += 0.7
            if term in text_l:
                score += 0.25
        if score > 0:
            scores[snippet.uri] = score
    return scores


def path_scoped_symbol(snippets: list[Any], record: dict[str, Any], query: str) -> dict[str, float]:
    """Symbol score gated/boosted by file/path scope from the original grep."""
    symbol_scores = exact_prefix_symbol(snippets, record, query)
    path_terms = infer_path_terms(record)
    scores: dict[str, float] = {}
    for snippet in snippets:
        base_score = symbol_scores.get(snippet.uri, 0.0)
        if base_score <= 0:
            continue
        rel_parts = split_identifier(snippet.rel)
        overlap = sum(1 for term in path_terms if term in rel_parts)
        # Do not hard-filter; old grep paths are sometimes absolute/noisy.
        scope_boost = 1.0 + min(overlap, 5) * 0.18
        scores[snippet.uri] = base_score * scope_boost
    return scores


def kind_aware_declaration(snippets: list[Any], record: dict[str, Any], query: str) -> dict[str, float]:
    """Use ctags kind buckets as a ranking feature."""
    symbol_scores = exact_prefix_symbol(snippets, record, query)
    boosts = kind_intent(query)
    scores: dict[str, float] = {}
    for snippet in snippets:
        score = symbol_scores.get(snippet.uri, 0.0)
        if score <= 0:
            continue
        scores[snippet.uri] = score * boosts.get(snippet.kind, 1.0)
    return scores


def identifier_split_abbrev(snippets: list[Any], record: dict[str, Any], query: str) -> dict[str, float]:
    """Identifier splitting plus acronym/abbreviation matching."""
    terms = query_terms(query)
    q_join = "".join(terms)
    q_acronym = "".join(term[:1] for term in terms if term)
    scores: dict[str, float] = {}
    for snippet in snippets:
        fields = [
            (split_identifier(snippet.symbol), 4.0),
            (split_identifier(snippet.signature), 1.8),
            (split_identifier(snippet.rel), 1.0),
        ]
        score = 0.0
        for parts, weight in fields:
            if not parts:
                continue
            joined = "".join(parts)
            acronym = "".join(part[:1] for part in parts)
            matched = sum(1 for term in terms if term in parts)
            if matched:
                score += weight * matched / max(len(terms), 1)
            if q_join and q_join in joined:
                score += weight * 0.7
            if len(q_acronym) >= 2 and q_acronym == acronym:
                score += weight * 1.4
            for term in terms:
                if len(term) >= 4:
                    best = max((SequenceMatcher(None, term, part).ratio() for part in parts), default=0.0)
                    if best >= 0.78:
                        score += weight * best * 0.25
        if score > 0:
            scores[snippet.uri] = score
    return scores


def field_rrf_symbol(snippets: list[Any], record: dict[str, Any], query: str) -> dict[str, float]:
    """Fuse independent symbol/signature/path/kind ranks with RRF."""
    terms = query_terms(query)
    boosts = kind_intent(query)
    field_scores: dict[str, dict[str, float]] = {"symbol": {}, "signature": {}, "path": {}, "kind": {}}
    for snippet in snippets:
        symbol_parts = split_identifier(snippet.symbol)
        sig_parts = split_identifier(snippet.signature)
        path_parts = split_identifier(snippet.rel)
        sym_score = sum(2.0 for term in terms if term in symbol_parts) + sum(0.9 for term in terms if term in norm_identifier(snippet.symbol))
        sig_score = sum(1.0 for term in terms if term in sig_parts)
        path_score = sum(1.0 for term in terms if term in path_parts)
        kind_score = sym_score * (boosts.get(snippet.kind, 1.0) - 0.95)
        if sym_score > 0:
            field_scores["symbol"][snippet.uri] = sym_score
        if sig_score > 0:
            field_scores["signature"][snippet.uri] = sig_score
        if path_score > 0:
            field_scores["path"][snippet.uri] = path_score
        if kind_score > 0:
            field_scores["kind"][snippet.uri] = kind_score

    out: dict[str, float] = {}
    weights = {"symbol": 1.0, "signature": 0.65, "path": 0.45, "kind": 0.35}
    for field, scores in field_scores.items():
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        for rank, (uri, _) in enumerate(ranked, start=1):
            out[uri] = out.get(uri, 0.0) + weights[field] / (60.0 + rank)
    return out


def hybrid_symbol_decl(snippets: list[Any], record: dict[str, Any], query: str) -> dict[str, float]:
    """Conservative hybrid of the strongest symbol-search inspired signals."""
    return combine(
        (ctags_current(snippets, record, query), 0.35),
        (exact_prefix_symbol(snippets, record, query), 0.30),
        (path_scoped_symbol(snippets, record, query), 0.15),
        (identifier_split_abbrev(snippets, record, query), 0.12),
        (kind_aware_declaration(snippets, record, query), 0.08),
    )


VARIANTS: dict[str, Callable[[list[Any], dict[str, Any], str], dict[str, float]]] = {
    "ctags_current_baseline": ctags_current,
    "exact_prefix_symbol": exact_prefix_symbol,
    "zoekt_like_symbol_signal": zoekt_like_symbol_signal,
    "path_scoped_symbol": path_scoped_symbol,
    "kind_aware_declaration": kind_aware_declaration,
    "identifier_split_abbrev": identifier_split_abbrev,
    "field_rrf_symbol": field_rrf_symbol,
    "hybrid_symbol_decl": hybrid_symbol_decl,
}


def empty_counts() -> dict[str, int]:
    return {"top1": 0, "top3": 0, "top5": 0}


def hit_metrics(hits: list[dict[str, Any]], targets: list[dict[str, Any]]) -> dict[str, bool]:
    return {
        "top1": any(base.hit_target(hit, targets, False) for hit in hits[:1]),
        "top3": any(base.hit_target(hit, targets, False) for hit in hits[:3]),
        "top5": any(base.hit_target(hit, targets, False) for hit in hits[:5]),
    }


def evaluate(dataset: Path, out_dir: Path, candidate_limit: int, max_snippets: int) -> dict[str, Any]:
    records = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {name: empty_counts() for name in VARIANTS}
    timings = {name: 0.0 for name in VARIANTS}
    usable = 0
    candidate_hit = 0
    candidate_time_total = 0.0
    snippet_counts: list[int] = []
    pred_path = out_dir / "ctags_route_predictions.jsonl"

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

            usable += 1
            candidate_time_total += candidate_time
            snippet_counts.append(len(snippets))
            candidate_hit += int(any(target["path"] in candidate_files for target in targets))
            out_row = {
                "record_index": idx,
                "instance_id": record.get("instance_id"),
                "query": query,
                "targets": targets,
                "candidate_file_count": len(candidate_files),
                "snippet_count": len(snippets),
                "variants": {},
            }
            for name, scorer in VARIANTS.items():
                score_start = time.perf_counter()
                scores = scorer(snippets, record, query)
                elapsed = time.perf_counter() - score_start
                timings[name] += elapsed
                hits = base.rank_route(snippets, scores, 5)
                metrics = hit_metrics(hits, targets)
                for key, value in metrics.items():
                    counts[name][key] += int(value)
                out_row["variants"][name] = {
                    "metrics": metrics,
                    "score_time_sec": elapsed,
                    "hits": hits[:5],
                }
            handle.write(json.dumps(out_row, ensure_ascii=False) + "\n")

    rows = []
    for name, route_counts in counts.items():
        rows.append({
            "variant": name,
            "top1": round(route_counts["top1"] / usable, 4) if usable else 0.0,
            "top3": round(route_counts["top3"] / usable, 4) if usable else 0.0,
            "top5": round(route_counts["top5"] / usable, 4) if usable else 0.0,
            "top1_count": route_counts["top1"],
            "top3_count": route_counts["top3"],
            "top5_count": route_counts["top5"],
            "avg_score_time_sec": round(timings[name] / usable, 6) if usable else 0.0,
        })
    rows.sort(key=lambda item: (item["top5"], item["top3"], item["top1"]), reverse=True)

    metrics = {
        "dataset": str(dataset),
        "predictions": str(pred_path),
        "experiment_scope": "canonical_ctags_symbol_route_variants",
        "metric": "grep candidate pool -> ctags/symbol route ranks snippets independently -> top1/top3/top5 hit",
        "usable_records": usable,
        "candidate_limit": candidate_limit,
        "max_snippets_per_record": max_snippets,
        "candidate_recall": round(candidate_hit / usable, 4) if usable else 0.0,
        "avg_snippets_per_search": round(sum(snippet_counts) / usable, 2) if usable else 0.0,
        "avg_candidate_build_sec": round(candidate_time_total / usable, 6) if usable else 0.0,
        "variants": rows,
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(metrics, out_dir / "ctags_route_variants.md")
    return metrics


def write_markdown(metrics: dict[str, Any], path: Path) -> None:
    lines = [
        "# Ctags / Symbol Route Variants",
        "",
        "Metric:",
        "",
        "```text",
        metrics["metric"],
        "```",
        "",
        f"- usable_records: `{metrics['usable_records']}`",
        f"- candidate_limit: `{metrics['candidate_limit']}`",
        f"- max_snippets_per_record: `{metrics['max_snippets_per_record']}`",
        f"- candidate_recall: `{metrics['candidate_recall']:.4f}`",
        f"- avg_snippets_per_search: `{metrics['avg_snippets_per_search']}`",
        "",
        "## Research Basis",
        "",
        "| variant | idea | reference |",
        "|---|---|---|",
        "| `exact_prefix_symbol` | Treat ctags output as a declaration index; rank exact and prefix declaration-name matches first. | Sourcegraph symbol search uses ctags to index declarations; Sourcegraph docs also mention exact and prefix symbol-search behavior. |",
        "| `zoekt_like_symbol_signal` | Use substring/trigram-like code-search matching, with symbol matches as a key ranking signal. | Zoekt is a trigram-based code search engine and recommends Universal Ctags because symbol information is a key ranking signal. |",
        "| `path_scoped_symbol` | Combine symbol matches with original grep path/scope, similar to file-qualified code-search queries. | Zoekt/Sourcegraph support file/path query qualifiers; Sourcegraph symbol behavior references path-prefix filtering for symbol sidebar use cases. |",
        "| `kind_aware_declaration` | Use ctags declaration categories: class/type/function/assignment. | Sourcegraph docs describe ctags symbols being categorized by declaration type in the symbol sidebar. |",
        "| `identifier_split_abbrev` | Split identifiers and support acronym/abbreviation matches. | Identifier splitting work such as Lingua::IdSplitter and Spiral targets compound code identifiers. |",
        "| `field_rrf_symbol` | Fuse independent symbol/signature/path/kind ranks. | Reciprocal Rank Fusion is a robust rank-combination baseline. |",
        "| `hybrid_symbol_decl` | Conservative blend of declaration-index signals. | Practical code-search engines combine multiple ranking signals rather than relying on one raw symbol score. |",
        "",
        "References:",
        "",
        "- Sourcegraph symbol search: https://sourcegraph.com/docs/code-search/types/symbol",
        "- Zoekt README: https://github.com/sourcegraph/zoekt",
        "- Universal Ctags manual: https://docs.ctags.io/en/stable/man/ctags.1.html",
        "- Sourcerer / structural code retrieval: https://doi.org/10.1016/j.scico.2012.04.008",
        "- Lingua::IdSplitter paper: https://doi.org/10.1016/j.jss.2014.08.031",
        "- Spiral identifier splitter: https://doi.org/10.21105/joss.00653",
        "- Reciprocal Rank Fusion: https://doi.org/10.1145/1571941.1572114",
        "",
        "## Results",
        "",
        "| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_score_time_sec |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in metrics["variants"]:
        lines.append(
            f"| `{row['variant']}` | {row['top1']:.4f} | {row['top3']:.4f} | {row['top5']:.4f} | "
            f"{row['top1_count']} | {row['top3_count']} | {row['top5_count']} | {row['avg_score_time_sec']:.6f} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(ROOT / "artifacts" / "legacy-search-dataset" / "search_targets.jsonl"))
    parser.add_argument("--out-dir", default=str(ROOT / "artifacts" / "ctags-route-exp"))
    parser.add_argument("--candidate-limit", type=int, default=80)
    parser.add_argument("--max-snippets", type=int, default=500)
    args = parser.parse_args()
    metrics = evaluate(Path(args.dataset), Path(args.out_dir), args.candidate_limit, args.max_snippets)
    print(json.dumps(metrics["variants"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
