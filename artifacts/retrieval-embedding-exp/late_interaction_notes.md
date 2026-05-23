# Embedding Route Variants

This note summarizes the embedding-route experiment and the idea behind the
`late_interaction_proxy` method.

## Referenced Work

| Work | Why It Matters Here |
|---|---|
| CodeSearchNet: *Evaluating the State of Semantic Code Search* | Frames code search as matching natural-language queries to code snippets, and highlights the vocabulary mismatch between user queries and code identifiers. |
| CodeBERT: *A Pre-Trained Model for Programming and Natural Languages* | Shows that code-specific pretraining can improve NL-code retrieval compared with generic text representations. |
| GraphCodeBERT: *Pre-training Code Representations with Data Flow* | Adds code structure/data-flow information to code representations, relevant to our graph route and future code-aware embeddings. |
| ColBERT: *Efficient and Effective Passage Search via Contextualized Late Interaction over BERT* | Main reference for late interaction: compare query/document at token level after encoding, instead of collapsing each side into one vector too early. |
| HyDE: *Precise Zero-Shot Dense Retrieval without Relevance Labels* | Motivation for query expansion / hypothetical document expansion. In our experiment, `query_plus_issue` is the closest proxy. |

## Original Embedding Proxy

The original embedding route behaves like a single-vector similarity method.

Process:

```text
query
  -> tokenize / embed-like representation
  -> one query vector

code snippet: path + symbol + signature + body
  -> tokenize / embed-like representation
  -> one snippet vector

score = cosine_similarity(query_vector, snippet_vector)
```

Example:

```text
query: "file upload permissions"

snippet:
  path: tests/file_storage/tests.py
  symbol: FileStoragePermissions
  signature: class FileStoragePermissions
  body: def test_file_upload_permissions(...)

score = one global query/snippet similarity
```

Weakness:

Large snippets can dilute important evidence. A strong symbol match like
`FileStoragePermissions` may not dominate if the body is long.

## Late Interaction Proxy

The late interaction route keeps query-token evidence separate.

Process:

```text
query tokens:
  file
  upload
  permissions

snippet fields:
  path
  symbol
  signature
  body

for each query token:
  find the best matching field/token in the snippet

score = sum(best_match_score(query_token) for each query_token)
```

Example:

```text
file        -> best match: path/body
upload      -> best match: body/signature
permissions -> best match: symbol/signature/body

final score = best(file) + best(upload) + best(permissions)
```

Why it helps code search:

- Symbol names and paths are often more important than raw body length.
- Query terms can match different fields independently.
- A long class body does not drown out a strong symbol/signature match.
- It approximates the ColBERT idea of token-level MaxSim, but cheaply.

## Experiment Result

Dataset:

```text
artifacts/legacy-search-dataset/search_targets.jsonl
```

Experiment output:

```text
artifacts/retrieval-embedding-exp/metrics.json
artifacts/retrieval-embedding-exp/route_accuracy.md
```

The experiment reranked the existing 4-route top-5 union from:

```text
artifacts/retrieval-eval/predictions.jsonl
```

Results:

| Variant | Top1 | Top3 | Top5 |
|---|---:|---:|---:|
| baseline_embedding_proxy | 0.2178 | 0.3366 | 0.4752 |
| late_interaction_proxy | 0.2970 | 0.5050 | 0.5644 |
| query_plus_issue | 0.2376 | 0.4851 | 0.5743 |
| field_weighted_embedding | 0.2970 | 0.3960 | 0.5149 |
| query_plus_legacy_scope | 0.2871 | 0.4059 | 0.5149 |
| pseudo_relevance_feedback | 0.1782 | 0.2871 | 0.3960 |

Interpretation:

`query_plus_issue` has the best Top5 on SWE-style tasks because SWE provides a
rich issue/problem statement. Outside SWE, this extra context may not exist.

`late_interaction_proxy` is the better general-purpose candidate because it only
needs normal code-search inputs: query, path, symbol, signature, and snippet
body.

