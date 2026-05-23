#!/usr/bin/env python3
"""Fixed-API embedding route variants.

This tests formatting/aggregation changes while keeping the embedding provider
and model fixed to the current OpenAI-compatible API.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sqlite3
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|0o[0-7]+|\d+")
CAMEL_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|[_\W]+")
CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")


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


def norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def split_identifier(text: str) -> list[str]:
    out: list[str] = []
    for part in re.split(CAMEL_RE, text or ""):
        if part:
            out.extend(t.lower() for t in TOKEN_RE.findall(part))
    return out


def query_split(query: str) -> str:
    parts = base.extract_query_terms(query)
    split_parts: list[str] = []
    for part in parts:
        split_parts.extend(split_identifier(part))
    merged = list(dict.fromkeys(parts + split_parts))
    return "code search query: " + query + "\nidentifiers: " + " ".join(merged)


def query_scope(record: dict[str, Any], query: str) -> str:
    search = record.get("search") or {}
    path = str(search.get("path") or "")
    command = str(search.get("command") or "")
    scope_bits = " ".join(Path(bit).name for bit in re.split(r"\s+", path + " " + command) if "/" in bit)
    return "\n".join([
        "code search query:",
        query,
        f"scope path: {path}",
        f"scope names: {scope_bits}",
    ])


def first_code(text: str, max_chars: int = 2400) -> str:
    return (text or "")[:max_chars]


def identifier_summary(snippet: Any, max_terms: int = 100) -> str:
    fields = " ".join([snippet.rel, snippet.symbol, snippet.signature, snippet.text])
    terms = [t.lower() for t in TOKEN_RE.findall(fields)]
    expanded: list[str] = []
    for term in terms:
        expanded.append(term)
        if "_" in term or any(c.isupper() for c in term):
            expanded.extend(split_identifier(term))
    counts = Counter(t for t in expanded if len(t) >= 2 and t not in base.STOP_TERMS)
    calls = [c for c in CALL_RE.findall(snippet.text or "") if c not in {"if", "for", "while", "return", "super"}]
    top = [term for term, _ in counts.most_common(max_terms)]
    return " ".join(dict.fromkeys([snippet.rel, snippet.symbol, snippet.signature, *calls[:30], *top]))


def doc_structured(snippet: Any) -> str:
    return "\n".join([
        "kind: python code snippet",
        f"path: {snippet.rel}",
        f"symbol: {snippet.symbol}",
        f"symbol_kind: {snippet.kind}",
        f"signature: {snippet.signature}",
        "code:",
        first_code(snippet.text),
    ])


def doc_identifier(snippet: Any) -> str:
    return "\n".join([
        "kind: python code identifiers",
        f"path: {snippet.rel}",
        f"symbol: {snippet.symbol}",
        f"signature: {snippet.signature}",
        f"identifiers: {identifier_summary(snippet)}",
    ])


def doc_path_symbol(snippet: Any) -> str:
    return f"path: {snippet.rel}\nsymbol: {snippet.symbol}\nkind: {snippet.kind}"


def doc_signature(snippet: Any) -> str:
    return f"path: {snippet.rel}\nsignature: {snippet.signature or snippet.symbol}"


class EmbeddingCache:
    def __init__(self, path: Path, *, model: str, base_url: str, api_key: str, dimensions: int, batch_size: int):
        self.path = path
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.dimensions = dimensions
        self.batch_size = batch_size
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS embeddings (key TEXT PRIMARY KEY, vector BLOB NOT NULL)"
        )
        self.conn.commit()

    def key(self, text: str) -> str:
        payload = f"{self.model}|{self.dimensions}|{text}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def get_many(self, texts: list[str]) -> dict[str, np.ndarray]:
        out: dict[str, np.ndarray] = {}
        keys = [self.key(text) for text in texts]
        for key in keys:
            row = self.conn.execute("SELECT vector FROM embeddings WHERE key=?", (key,)).fetchone()
            if row:
                out[key] = np.frombuffer(row[0], dtype=np.float32)
        missing = [(key, text) for key, text in zip(keys, texts) if key not in out]
        for start in range(0, len(missing), self.batch_size):
            batch = missing[start:start + self.batch_size]
            vectors = self.fetch([text for _, text in batch])
            with self.conn:
                for (key, _text), vector in zip(batch, vectors):
                    arr = np.asarray(vector, dtype=np.float32)
                    norm = float(np.linalg.norm(arr))
                    if norm > 0:
                        arr = arr / norm
                    out[key] = arr
                    self.conn.execute("INSERT OR REPLACE INTO embeddings VALUES (?, ?)", (key, arr.tobytes()))
        return out

    def fetch(self, texts: list[str]) -> list[list[float]]:
        url = self.base_url + ("/embeddings" if self.base_url.endswith("/v1") else "/v1/embeddings")
        body = {"model": self.model, "input": texts}
        if self.dimensions:
            body["dimensions"] = self.dimensions
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return [item["embedding"] for item in sorted(payload["data"], key=lambda x: x["index"])]

    def embed_texts(self, texts: list[str]) -> list[np.ndarray]:
        texts = [norm_text(text) for text in texts]
        got = self.get_many(texts)
        return [got[self.key(text)] for text in texts]


def dot_scores(query_vec: np.ndarray, docs: list[tuple[str, np.ndarray]]) -> dict[str, float]:
    return {uri: float(np.dot(query_vec, vec)) for uri, vec in docs}


def lexical_cosine(query: str, doc: str) -> float:
    q = Counter(base.tokenize(query))
    d = Counter(base.tokenize(doc))
    if not q or not d:
        return 0.0
    dot = sum(q.get(term, 0) * value for term, value in d.items())
    if dot <= 0:
        return 0.0
    qn = sum(v * v for v in q.values()) ** 0.5
    dn = sum(v * v for v in d.values()) ** 0.5
    return dot / max(qn * dn, 1e-9)


def score_proxy(snippets: list[Any], record: dict[str, Any], query: str) -> dict[str, dict[str, float]]:
    structured = {s.uri: doc_structured(s) for s in snippets}
    identifier = {s.uri: doc_identifier(s) for s in snippets}
    path_symbol = {s.uri: doc_path_symbol(s) for s in snippets}
    signature = {s.uri: doc_signature(s) for s in snippets}
    q_raw = "code search query: " + query
    q_split = query_split(query)
    q_scope = query_scope(record, query)
    scores = {
        "api_structured_raw_query": {uri: lexical_cosine(q_raw, doc) for uri, doc in structured.items()},
        "api_structured_identifier_query": {uri: lexical_cosine(q_split, doc) for uri, doc in structured.items()},
        "api_identifier_summary": {uri: lexical_cosine(q_split, doc) for uri, doc in identifier.items()},
        "api_scope_query": {uri: lexical_cosine(q_scope, doc) for uri, doc in structured.items()},
    }
    field_rankings = [
        rank_uris({uri: lexical_cosine(q_split, doc) for uri, doc in path_symbol.items()}, len(snippets)),
        rank_uris({uri: lexical_cosine(q_split, doc) for uri, doc in signature.items()}, len(snippets)),
        rank_uris({uri: lexical_cosine(q_split, doc) for uri, doc in identifier.items()}, len(snippets)),
    ]
    scores["api_field_rrf"] = rrf_from_rankings(field_rankings)
    return scores


def rank_uris(scores: dict[str, float], limit: int) -> list[str]:
    return [uri for uri, score in sorted(scores.items(), key=lambda item: item[1], reverse=True) if score > 0][:limit]


def rrf_from_rankings(rankings: list[list[str]], k: float = 60.0) -> dict[str, float]:
    out: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, uri in enumerate(ranking, start=1):
            out[uri] += 1.0 / (k + rank)
    return dict(out)


def hit_metrics(hits: list[dict[str, Any]], targets: list[dict[str, Any]]) -> dict[str, bool]:
    return {
        "top1": any(base.hit_target(hit, targets, False) for hit in hits[:1]),
        "top3": any(base.hit_target(hit, targets, False) for hit in hits[:3]),
        "top5": any(base.hit_target(hit, targets, False) for hit in hits[:5]),
    }


def rank_hits(snippets_by_uri: dict[str, Any], scores: dict[str, float]) -> list[dict[str, Any]]:
    ranked = [(score, snippets_by_uri[uri]) for uri, score in scores.items() if uri in snippets_by_uri]
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [base.snippet_dict(snippet, score) for score, snippet in ranked[:5]]


def evaluate(dataset: Path, out_dir: Path, *, candidate_limit: int, max_snippets: int, dimensions: int, batch_size: int, backend: str) -> dict[str, Any]:
    model = os.environ.get("RTC_EMBEDDING_MODEL") or "text-embedding-3-small"
    base_url = os.environ.get("RTC_EMBEDDING_BASE_URL") or "https://api.openai-proxy.org"
    out_dir.mkdir(parents=True, exist_ok=True)
    cache = None
    if backend == "api":
        api_key = os.environ.get("RTC_EMBEDDING_API_KEY") or ""
        if not api_key:
            raise RuntimeError("RTC_EMBEDDING_API_KEY is not set")
        cache = EmbeddingCache(out_dir / "embedding_cache.sqlite", model=model, base_url=base_url, api_key=api_key, dimensions=dimensions, batch_size=batch_size)

    variants = [
        "api_structured_raw_query",
        "api_structured_identifier_query",
        "api_identifier_summary",
        "api_scope_query",
        "api_field_rrf",
    ]
    counts = {name: {"top1": 0, "top3": 0, "top5": 0} for name in variants}
    timings = defaultdict(float)
    records = [json.loads(line) for line in dataset.read_text().splitlines() if line.strip()]
    usable = 0
    candidate_hit = 0
    pred_path = out_dir / "api_embedding_predictions.jsonl"
    with pred_path.open("w", encoding="utf-8") as handle:
        for idx, record in enumerate(records, start=1):
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
            by_uri = {snippet.uri: snippet for snippet in snippets}

            embed_start = time.perf_counter()
            if backend == "proxy":
                scores_by_variant = score_proxy(snippets, record, query)
            else:
                assert cache is not None
                structured_texts = [doc_structured(s) for s in snippets]
                identifier_texts = [doc_identifier(s) for s in snippets]
                path_symbol_texts = [doc_path_symbol(s) for s in snippets]
                signature_texts = [doc_signature(s) for s in snippets]
                q_raw_text = "code search query: " + query
                q_split_text = query_split(query)
                q_scope_text = query_scope(record, query)

                all_texts = [q_raw_text, q_split_text, q_scope_text] + structured_texts + identifier_texts + path_symbol_texts + signature_texts
                all_vecs = cache.embed_texts(all_texts)
                q_raw, q_split, q_scope = all_vecs[:3]
                offset = 3
                structured_vecs = all_vecs[offset:offset + len(snippets)]
                offset += len(snippets)
                identifier_vecs = all_vecs[offset:offset + len(snippets)]
                offset += len(snippets)
                path_symbol_vecs = all_vecs[offset:offset + len(snippets)]
                offset += len(snippets)
                signature_vecs = all_vecs[offset:offset + len(snippets)]

                doc_structured_pairs = [(s.uri, v) for s, v in zip(snippets, structured_vecs)]
                doc_identifier_pairs = [(s.uri, v) for s, v in zip(snippets, identifier_vecs)]
                doc_path_pairs = [(s.uri, v) for s, v in zip(snippets, path_symbol_vecs)]
                doc_sig_pairs = [(s.uri, v) for s, v in zip(snippets, signature_vecs)]

                scores_by_variant = {
                    "api_structured_raw_query": dot_scores(q_raw, doc_structured_pairs),
                    "api_structured_identifier_query": dot_scores(q_split, doc_structured_pairs),
                    "api_identifier_summary": dot_scores(q_split, doc_identifier_pairs),
                    "api_scope_query": dot_scores(q_scope, doc_structured_pairs),
                }
                field_rankings = [
                    rank_uris(dot_scores(q_split, doc_path_pairs), len(snippets)),
                    rank_uris(dot_scores(q_split, doc_sig_pairs), len(snippets)),
                    rank_uris(dot_scores(q_split, doc_identifier_pairs), len(snippets)),
                ]
                scores_by_variant["api_field_rrf"] = rrf_from_rankings(field_rankings)
            timings["embedding_api_and_cache"] += time.perf_counter() - embed_start

            out_row = {"record_index": idx, "instance_id": record.get("instance_id"), "query": query, "targets": targets, "variants": {}}
            for name, scores in scores_by_variant.items():
                hits = rank_hits(by_uri, scores)
                metrics = hit_metrics(hits, targets)
                for key, value in metrics.items():
                    counts[name][key] += int(value)
                out_row["variants"][name] = {"metrics": metrics, "hits": [h["uri"] for h in hits[:5]]}
            handle.write(json.dumps(out_row, ensure_ascii=False) + "\n")

    table = []
    for name in variants:
        table.append({
            "variant": name,
            "top1": round(counts[name]["top1"] / usable, 4),
            "top3": round(counts[name]["top3"] / usable, 4),
            "top5": round(counts[name]["top5"] / usable, 4),
            "top1_count": counts[name]["top1"],
            "top3_count": counts[name]["top3"],
            "top5_count": counts[name]["top5"],
        })
    table.sort(key=lambda row: (row["top5"], row["top3"], row["top1"]), reverse=True)
    metrics = {
        "dataset": str(dataset),
        "predictions": str(pred_path),
        "experiment_scope": "fixed_api_embedding_model_formatting_variants",
        "model": model,
        "backend": backend,
        "dimensions": dimensions,
        "usable_records": usable,
        "candidate_limit": candidate_limit,
        "max_snippets_per_record": max_snippets,
        "candidate_recall": round(candidate_hit / usable, 4),
        "avg_embedding_api_and_cache_sec": round(timings["embedding_api_and_cache"] / usable, 6),
        "variants": table,
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n")
    lines = [
        "# Fixed API Embedding Variants",
        "",
        f"- model: `{model}`",
        f"- backend: `{backend}`",
        f"- dimensions: `{dimensions}`",
        f"- usable_records: `{usable}`",
        f"- candidate_limit: `{candidate_limit}`",
        f"- max_snippets_per_record: `{max_snippets}`",
        f"- candidate_recall: `{metrics['candidate_recall']:.4f}`",
        f"- avg_embedding_api_and_cache_sec: `{metrics['avg_embedding_api_and_cache_sec']:.6f}`",
        "",
        "| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in table:
        lines.append(f"| {row['variant']} | {row['top1']:.4f} | {row['top3']:.4f} | {row['top5']:.4f} | {row['top1_count']} | {row['top3_count']} | {row['top5_count']} |")
    (out_dir / "api_embedding_variants.md").write_text("\n".join(lines) + "\n")
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(ROOT / "artifacts" / "legacy-search-dataset" / "search_targets.jsonl"))
    parser.add_argument("--out-dir", default=str(ROOT / "artifacts" / "api-embedding-exp"))
    parser.add_argument("--candidate-limit", type=int, default=80)
    parser.add_argument("--max-snippets", type=int, default=200)
    parser.add_argument("--dimensions", type=int, default=512)
    parser.add_argument("--batch-size", type=int, default=96)
    parser.add_argument("--backend", choices=["api", "proxy"], default="api")
    args = parser.parse_args()
    metrics = evaluate(Path(args.dataset), Path(args.out_dir), candidate_limit=args.candidate_limit, max_snippets=args.max_snippets, dimensions=args.dimensions, batch_size=args.batch_size, backend=args.backend)
    print(json.dumps(metrics["variants"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
