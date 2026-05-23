#!/usr/bin/env python3
"""Offline RTC-style retrieval evaluator for legacy grep -> target traces.

This is deliberately standalone so we can tune retrieval behavior in artifacts
without launching Claude or the MCP server. It recreates the shape of the RTC
code search path:

1. extract grep/query terms
2. narrow to candidate files
3. build L2-ish code snippets
4. score with route-specific scorers
5. evaluate route top-1/3/5 and fused top-1/3/5
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import re
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


CODE_EXTENSIONS = {
    ".py", ".pyi", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs",
    ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".scala",
    ".kt", ".kts", ".swift", ".m", ".mm", ".sh", ".bash", ".zsh",
    ".toml", ".yaml", ".yml", ".json", ".ini", ".cfg", ".txt", ".rst",
    ".md",
}
IGNORED_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", ".mypy_cache", ".pytest_cache",
    ".tox", ".venv", "venv", "env", "node_modules", "dist", "build",
    ".cache", "site-packages",
}
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|0o[0-7]+|\d+")
STOP_TERMS = {
    "the", "and", "for", "with", "from", "this", "that", "when", "then",
    "else", "none", "true", "false", "test", "tests", "file", "code",
    "line", "lines", "grep", "head", "tail", "include", "python",
}


@dataclass
class Snippet:
    uri: str
    rel: str
    symbol: str
    kind: str
    start_line: int
    end_line: int
    signature: str
    text: str


def snippet_dict(snippet: Snippet, score: float, scores: dict[str, float] | None = None) -> dict[str, Any]:
    return {
        **asdict(snippet),
        "score": float(score),
        "scores": scores or {},
    }


def tokenize(text: str) -> list[str]:
    parts: list[str] = []
    for raw in TOKEN_RE.findall(text):
        token = raw.lower()
        parts.append(token)
        if "_" in token:
            parts.extend(p for p in token.split("_") if p)
    return parts


def extract_query_terms(query: str) -> list[str]:
    terms: list[str] = []
    for term in tokenize(query):
        if len(term) < 2 and not term.isdigit():
            continue
        if term in STOP_TERMS:
            continue
        if term not in terms:
            terms.append(term)
    return terms[:12]


def safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def is_code_path(path: Path) -> bool:
    if path.suffix.lower() not in CODE_EXTENSIONS:
        return False
    return not any(part in IGNORED_DIRS for part in path.parts)


FILE_CACHE: dict[str, list[tuple[str, str]]] = {}
SNIPPET_CACHE: dict[tuple[str, str], list[Snippet]] = {}


def iter_code_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and is_code_path(path.relative_to(root)):
            out.append(path)
    return out


def workspace_files(root: Path) -> list[tuple[str, str]]:
    key = str(root.resolve())
    cached = FILE_CACHE.get(key)
    if cached is not None:
        return cached
    files: list[tuple[str, str]] = []
    for full in iter_code_files(root):
        rel = full.relative_to(root).as_posix()
        files.append((rel, safe_read(full).lower()))
    FILE_CACHE[key] = files
    return files


def collect_candidate_files(root: Path, query: str, limit: int) -> list[str]:
    terms = extract_query_terms(query)
    if not terms:
        return []
    scored: list[tuple[tuple[int, int, int, str], str]] = []
    for rel, text in workspace_files(root):
        full = root / rel
        rel_l = rel.lower()
        path_score = sum(20 for term in terms if term in rel_l)
        content_hits = sum(min(text.count(term), 8) for term in terms)
        if path_score <= 0 and content_hits <= 0:
            continue
        basename_score = sum(8 for term in terms if term in full.name.lower())
        scored.append(((path_score + basename_score + content_hits, path_score, content_hits, rel), rel))
    scored.sort(reverse=True)
    return [rel for _, rel in scored[:limit]]


def node_name(node: ast.AST) -> str:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return node.name
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        names: list[str] = []
        for target in targets:
            if isinstance(target, ast.Name):
                names.append(target.id)
            elif isinstance(target, ast.Attribute):
                names.append(target.attr)
        return ",".join(names)
    return ""


def node_kind(node: ast.AST) -> str:
    if isinstance(node, ast.ClassDef):
        return "type"
    if isinstance(node, ast.AsyncFunctionDef):
        return "async_function"
    if isinstance(node, ast.FunctionDef):
        return "function"
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        return "assignment"
    return "code"


def node_signature(lines: list[str], start: int) -> str:
    if 1 <= start <= len(lines):
        return lines[start - 1].strip()[:240]
    return ""


def slice_text(lines: list[str], start: int, end: int) -> str:
    start = max(1, start)
    end = min(len(lines), max(start, end))
    return "\n".join(lines[start - 1:end])


def build_python_snippets(root: Path, rel: str) -> list[Snippet]:
    full = root / rel
    text = safe_read(full)
    lines = text.splitlines()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    snippets: list[Snippet] = []
    wanted = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, ast.Assign, ast.AnnAssign)
    for node in ast.walk(tree):
        if not isinstance(node, wanted):
            continue
        start = int(getattr(node, "lineno", 1) or 1)
        end = int(getattr(node, "end_lineno", start) or start)
        name = node_name(node)
        if not name:
            continue
        # Keep assignment chunks small; they are crucial for settings/defaults.
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            end = min(end, start + 3)
        snippet_text = slice_text(lines, start, end)
        uri = f"{rel}#L{start}-L{end}:{name}"
        snippets.append(
            Snippet(
                uri=uri,
                rel=rel,
                symbol=name,
                kind=node_kind(node),
                start_line=start,
                end_line=end,
                signature=node_signature(lines, start),
                text=snippet_text,
            )
        )
    snippets.sort(key=lambda item: (item.start_line, item.end_line, item.symbol))
    return snippets


def build_fallback_snippets(root: Path, rel: str, max_lines: int = 80) -> list[Snippet]:
    lines = safe_read(root / rel).splitlines()
    snippets: list[Snippet] = []
    for start in range(1, len(lines) + 1, max_lines):
        end = min(len(lines), start + max_lines - 1)
        text = slice_text(lines, start, end)
        symbol = Path(rel).name
        snippets.append(
            Snippet(
                uri=f"{rel}#L{start}-L{end}:{symbol}",
                rel=rel,
                symbol=symbol,
                kind="code",
                start_line=start,
                end_line=end,
                signature=symbol,
                text=text,
            )
        )
    return snippets


def build_snippets(root: Path, candidate_files: list[str]) -> list[Snippet]:
    snippets: list[Snippet] = []
    root_key = str(root.resolve())
    for rel in candidate_files:
        cache_key = (root_key, rel)
        file_snippets = SNIPPET_CACHE.get(cache_key)
        if file_snippets is None:
            if rel.endswith((".py", ".pyi")):
                file_snippets = build_python_snippets(root, rel)
            else:
                file_snippets = []
            if not file_snippets:
                file_snippets = build_fallback_snippets(root, rel)
            SNIPPET_CACHE[cache_key] = file_snippets
        snippets.extend(file_snippets)
    return snippets


def bm25_scores(snippets: list[Snippet], query: str) -> dict[str, float]:
    q_terms = tokenize(query)
    docs = [tokenize(" ".join([s.rel, s.symbol, s.signature, s.text])) for s in snippets]
    if not q_terms or not docs:
        return {}
    avgdl = sum(len(doc) for doc in docs) / max(1, len(docs))
    dfs: Counter[str] = Counter()
    for doc in docs:
        for term in set(doc):
            dfs[term] += 1
    scores: dict[str, float] = {}
    for snippet, doc in zip(snippets, docs):
        tf = Counter(doc)
        score = 0.0
        for term in q_terms:
            df = dfs.get(term, 0)
            freq = tf.get(term, 0)
            if not df or not freq:
                continue
            idf = math.log(1.0 + (len(docs) - df + 0.5) / (df + 0.5))
            denom = freq + 1.5 * (1 - 0.75 + 0.75 * (len(doc) / max(avgdl, 1e-9)))
            score += idf * ((freq * 2.5) / max(denom, 1e-9))
        if score > 0:
            scores[snippet.uri] = score
    return scores


def ctags_scores(snippets: list[Snippet], query: str) -> dict[str, float]:
    terms = extract_query_terms(query)
    scores: dict[str, float] = {}
    for snippet in snippets:
        symbol = snippet.symbol.lower()
        rel = snippet.rel.lower()
        signature = snippet.signature.lower()
        score = 0.0
        for term in terms:
            if term == symbol:
                score += 3.0
            elif term in symbol:
                score += 1.5
            if term in signature:
                score += 1.0
            if term in rel:
                score += 0.6
        if snippet.kind in {"type", "function", "assignment"} and snippet.kind in query.lower():
            score += 0.8
        if score > 0:
            scores[snippet.uri] = score
    return scores


def embedding_proxy_scores(snippets: list[Snippet], query: str) -> dict[str, float]:
    """Lexical cosine proxy for embeddings in this offline artifact.

    It is not the production embedding model. It is useful for weight tuning
    experiments because it behaves like a broader bag-of-words semantic route.
    """
    q = Counter(tokenize(query))
    if not q:
        return {}
    q_norm = math.sqrt(sum(v * v for v in q.values()))
    scores: dict[str, float] = {}
    for snippet in snippets:
        doc = Counter(tokenize(" ".join([snippet.rel, snippet.symbol, snippet.signature, snippet.text])))
        if not doc:
            continue
        dot = sum(q.get(term, 0) * freq for term, freq in doc.items())
        if dot <= 0:
            continue
        d_norm = math.sqrt(sum(v * v for v in doc.values()))
        score = dot / max(q_norm * d_norm, 1e-9)
        if score > 0:
            scores[snippet.uri] = score
    return scores


def graph_proxy_scores(snippets: list[Snippet], query: str) -> dict[str, float]:
    """Tiny graph-route proxy using lexical anchors plus same-file expansion."""
    terms = extract_query_terms(query)
    if not terms:
        return {}
    anchor_scores = ctags_scores(snippets, query)
    for snippet in snippets:
        text_l = snippet.text.lower()
        relationish = sum(
            text_l.count(term)
            for term in terms
            if term in snippet.symbol.lower() or term in snippet.signature.lower() or term in snippet.rel.lower()
        )
        if relationish:
            anchor_scores[snippet.uri] = max(anchor_scores.get(snippet.uri, 0.0), min(relationish, 3) * 0.8)

    by_file: dict[str, list[Snippet]] = {}
    by_uri = {snippet.uri: snippet for snippet in snippets}
    for snippet in snippets:
        by_file.setdefault(snippet.rel, []).append(snippet)

    scores: dict[str, float] = {}
    for uri, anchor_score in anchor_scores.items():
        snippet = by_uri.get(uri)
        if not snippet:
            continue
        scores[uri] = max(scores.get(uri, 0.0), anchor_score + 1.0)
        for neighbor in by_file.get(snippet.rel, []):
            if neighbor.uri == uri:
                continue
            distance = abs(neighbor.start_line - snippet.start_line)
            if distance > 160:
                continue
            proximity = 1.0 / (1.0 + distance / 40.0)
            scores[neighbor.uri] = max(scores.get(neighbor.uri, 0.0), anchor_score * 0.45 + proximity)
    return scores


def normalize(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        return {}
    vals = list(scores.values())
    low, high = min(vals), max(vals)
    if high <= low:
        return {key: 1.0 for key in scores}
    return {key: (value - low) / (high - low) for key, value in scores.items()}


def route_score_maps(snippets: list[Snippet], query: str) -> dict[str, dict[str, float]]:
    return {
        "embedding_proxy": embedding_proxy_scores(snippets, query),
        "bm25": bm25_scores(snippets, query),
        "ctags": ctags_scores(snippets, query),
        "graph_proxy": graph_proxy_scores(snippets, query),
    }


def rank_route(snippets: list[Snippet], scores: dict[str, float], limit: int) -> list[dict[str, Any]]:
    by_uri = {snippet.uri: snippet for snippet in snippets}
    ranked = [
        (score, by_uri[uri])
        for uri, score in scores.items()
        if uri in by_uri and score > 0
    ]
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [snippet_dict(snippet, score) for score, snippet in ranked[:limit]]


def rank_fused_from_routes(
    snippets: list[Snippet],
    route_scores: dict[str, dict[str, float]],
    route_hits: dict[str, list[dict[str, Any]]],
    *,
    top_k: int,
    weights: dict[str, float],
) -> list[dict[str, Any]]:
    by_uri = {snippet.uri: snippet for snippet in snippets}
    normed = {route: normalize(scores) for route, scores in route_scores.items()}
    candidate_uris: set[str] = set()
    for hits in route_hits.values():
        candidate_uris.update(str(hit["uri"]) for hit in hits[:5])

    ranked: list[tuple[float, Snippet, dict[str, float]]] = []
    for uri in candidate_uris:
        snippet = by_uri.get(uri)
        if not snippet:
            continue
        parts = {route: normed.get(route, {}).get(uri, 0.0) for route in weights}
        score = sum(weights[route] * parts.get(route, 0.0) for route in weights)
        ranked.append((score, snippet, parts))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [snippet_dict(snippet, score, parts) for score, snippet, parts in ranked[:top_k]]


def parse_first_line_number(content: str) -> int | None:
    for line in content.splitlines():
        match = re.match(r"\s*(\d+)\s+", line)
        if match:
            return int(match.group(1))
    return None


def positive_targets(record: dict[str, Any]) -> list[dict[str, Any]]:
    targets = []
    workspace = Path(record.get("workspace") or "")
    for target in record.get("targets") or []:
        rel = str(target.get("path") or "")
        if not rel or rel == "TASK.md" or rel == "RUN_IN_SWE_LOCAL_ENV.sh":
            continue
        if Path(rel).is_absolute():
            try:
                rel = Path(rel).resolve().relative_to(workspace.resolve()).as_posix()
            except Exception:
                pass
        rel = Path(rel).as_posix().lstrip("./")
        if not is_code_path(Path(rel)):
            continue
        if not (workspace / rel).exists():
            continue
        line = parse_first_line_number(((target.get("result") or {}).get("content")) or "")
        targets.append({"path": rel, "line": line, "kind": target.get("kind")})
    deduped = []
    seen = set()
    for target in targets:
        key = (target["path"], target.get("line"))
        if key not in seen:
            seen.add(key)
            deduped.append(target)
    return deduped


def hit_target(hit: dict[str, Any], targets: list[dict[str, Any]], require_line: bool) -> bool:
    for target in targets:
        if hit["rel"] != target["path"]:
            continue
        line = target.get("line")
        if not require_line or line is None:
            return True
        if int(hit["start_line"]) <= int(line) <= int(hit["end_line"]):
            return True
    return False


def empty_route_counts() -> dict[str, int]:
    return {"top1": 0, "top3": 0, "top5": 0}


def route_accuracy_row(route: str, counts: dict[str, int], usable: int) -> dict[str, Any]:
    def ratio(key: str) -> float:
        return round(counts.get(key, 0) / usable, 4) if usable else 0.0

    return {
        "route": route,
        "top1": ratio("top1"),
        "top3": ratio("top3"),
        "top5": ratio("top5"),
        "top1_count": counts.get("top1", 0),
        "top3_count": counts.get("top3", 0),
        "top5_count": counts.get("top5", 0),
    }


def evaluate(dataset_path: Path, out_dir: Path, *, candidate_limit: int, top_k: int, require_line: bool) -> dict[str, Any]:
    weights = {
        "embedding_proxy": 0.45,
        "bm25": 0.25,
        "ctags": 0.15,
        "graph_proxy": 0.15,
    }
    rows = [json.loads(line) for line in dataset_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    out_dir.mkdir(parents=True, exist_ok=True)
    pred_path = out_dir / "predictions.jsonl"

    total = usable = candidate_hit = 0
    route_counts = {
        "embedding_proxy": empty_route_counts(),
        "bm25": empty_route_counts(),
        "ctags": empty_route_counts(),
        "graph_proxy": empty_route_counts(),
        "fused": empty_route_counts(),
    }
    with pred_path.open("w", encoding="utf-8") as handle:
        for idx, record in enumerate(rows, start=1):
            total += 1
            root = Path(record.get("workspace") or "")
            query = str((record.get("search") or {}).get("query") or "")
            targets = positive_targets(record)
            if not root.is_dir() or not query or not targets:
                continue
            usable += 1
            candidate_files = collect_candidate_files(root, query, candidate_limit)
            if any(target["path"] in candidate_files for target in targets):
                candidate_hit += 1
            snippets = build_snippets(root, candidate_files)
            scores_by_route = route_score_maps(snippets, query)
            route_hits = {
                route: rank_route(snippets, scores, max(top_k, 5))
                for route, scores in scores_by_route.items()
            }
            fused_hits = rank_fused_from_routes(
                snippets,
                scores_by_route,
                route_hits,
                top_k=top_k,
                weights=weights,
            )
            all_hits = {**route_hits, "fused": fused_hits}
            record_route_metrics: dict[str, dict[str, bool]] = {}
            for route, hits in all_hits.items():
                route_top1 = any(hit_target(hit, targets, require_line) for hit in hits[:1])
                route_top3 = any(hit_target(hit, targets, require_line) for hit in hits[:3])
                route_top5 = any(hit_target(hit, targets, require_line) for hit in hits[:5])
                route_counts[route]["top1"] += int(route_top1)
                route_counts[route]["top3"] += int(route_top3)
                route_counts[route]["top5"] += int(route_top5)
                record_route_metrics[route] = {
                    "top1": route_top1,
                    "top3": route_top3,
                    "top5": route_top5,
                }
            handle.write(json.dumps({
                "record_index": idx,
                "instance_id": record.get("instance_id"),
                "repo": record.get("repo"),
                "query": query,
                "targets": targets,
                "candidate_count": len(candidate_files),
                "candidate_hit": any(target["path"] in candidate_files for target in targets),
                "route_metrics": record_route_metrics,
                "hits_by_route": {
                    route: hits[:5]
                    for route, hits in all_hits.items()
                },
            }, ensure_ascii=False) + "\n")

    def ratio(value: int) -> float:
        return round(value / usable, 4) if usable else 0.0

    route_table = [
        route_accuracy_row(route, route_counts[route], usable)
        for route in ("embedding_proxy", "bm25", "ctags", "graph_proxy", "fused")
    ]
    metrics = {
        "dataset": str(dataset_path),
        "predictions": str(pred_path),
        "total_records": total,
        "usable_records": usable,
        "candidate_limit": candidate_limit,
        "top_k": top_k,
        "require_line": require_line,
        "weights": weights,
        "candidate_recall": ratio(candidate_hit),
        "route_accuracy": route_table,
        "counts": {
            "candidate_hit": candidate_hit,
            "routes": route_counts,
        },
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    table_lines = [
        "| route | top1 | top3 | top5 | top1_count | top3_count | top5_count |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in route_table:
        table_lines.append(
            f"| {row['route']} | {row['top1']:.4f} | {row['top3']:.4f} | {row['top5']:.4f} | "
            f"{row['top1_count']} | {row['top3_count']} | {row['top5_count']} |"
        )
    (out_dir / "route_accuracy.md").write_text("\n".join(table_lines) + "\n", encoding="utf-8")
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="../legacy-search-dataset/search_targets.jsonl")
    parser.add_argument("--out-dir", default=".")
    parser.add_argument("--candidate-limit", type=int, default=80)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--require-line", action="store_true")
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    dataset = Path(args.dataset)
    if not dataset.is_absolute():
        dataset = (here / dataset).resolve()
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = (here / out_dir).resolve()
    metrics = evaluate(dataset, out_dir, candidate_limit=args.candidate_limit, top_k=args.top_k, require_line=args.require_line)
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
