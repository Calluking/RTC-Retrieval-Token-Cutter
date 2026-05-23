# Embedding Route Research

This note starts the redo of **step 2 route optimization** under the correct
metric:

```text
grep candidate pool -> embedding route ranks snippets independently -> top1/top3/top5 hit
```

The earlier embedding experiments mixed this up with final reranking. Those
results are still useful as reranker hints, but this document is about the
embedding route as a standalone candidate generator.

## Current Canonical Result

Canonical benchmark:

```text
artifacts/retrieval-canonical-variant-benchmark/canonical_variant_benchmark.md
```

Current embedding variants under the correct route metric:

| variant | top1 | top3 | top5 | note |
|---|---:|---:|---:|---|
| `query_plus_legacy_scope` | 0.3663 | 0.4950 | 0.5644 | Best, but uses grep path/command scope. |
| `field_weighted_embedding` | 0.3069 | 0.3960 | 0.4950 | Best query-only-ish handcrafted scorer. |
| `late_interaction_proxy` | 0.2772 | 0.4455 | 0.4851 | Better Top3, unchanged Top5 vs baseline. |
| `baseline_embedding_proxy` | 0.2178 | 0.3366 | 0.4851 | Current lexical cosine proxy. |
| `pseudo_relevance_feedback` | 0.1584 | 0.2475 | 0.3069 | Bad under route metric. |
| `query_plus_issue` | 0.0891 | 0.1584 | 0.2277 | Bad as route scorer; too much noisy issue text. |

Important interpretation:

- `late_interaction_proxy` looked good in rerank-union experiments, but as an
  independent embedding route it is only Top5 `0.4851`.
- `query_plus_legacy_scope` is strong because it uses path/scope information.
  If production `search_code` has path hints, this is a real signal. If not,
  do not count it as a pure embedding solution.

## Fixed API Model Constraint

The current RTC runners are wired to an OpenAI-compatible embedding API:

```text
EMBEDDING_PROVIDER=openai
RTC_EMBEDDING_MODEL=text-embedding-3-small
RTC_EMBEDDING_BASE_URL=https://api.openai-proxy.org
```

The repo default has been moved to `text-embedding-3-small` for cost control.
`text-embedding-3-large` remains available by explicitly setting
`RTC_EMBEDDING_MODEL=text-embedding-3-large`.

Implication:

```text
Do not optimize by switching embedding model families first.
Optimize how we use the fixed API model.
```

OpenAI API facts that matter for this route:

- `text-embedding-3-large` outputs 3072-dimensional vectors by default.
- `text-embedding-3-small` outputs 1536-dimensional vectors by default.
- The embedding API supports a `dimensions` parameter for v3 embedding models.
- The embedding input max is 8192 tokens per item.
- OpenAI recommends cosine similarity; v3 embeddings are normalized, so dot
  product gives the same ranking as cosine and is cheaper to compute.
- The API accepts arrays of inputs, so batching snippet embeddings matters.

References:

- OpenAI embeddings guide: https://platform.openai.com/docs/guides/embeddings
- OpenAI embeddings API reference: https://platform.openai.com/docs/api-reference/embeddings
- `text-embedding-3-large` model page: https://platform.openai.com/docs/models/text-embedding-3-large
- `text-embedding-3-small` model page: https://platform.openai.com/docs/models/text-embedding-3-small

## Research Directions For The Current API Model

### 1. Structured Input Formatting

The model is fixed, but the string we embed is not. For code search this is
probably the highest-leverage knob.

Current L2-ish text is roughly:

```text
# path (lines)

code body
```

Better embedding documents should expose fields explicitly:

```text
kind: python code snippet
path: django/core/files/storage.py
symbol: FileSystemStorage
signature: class FileSystemStorage(Storage)
relations: calls get_storage_class; contains _save; imports settings
code:
...
```

Variants to test:

| variant | description |
|---|---|
| `api_doc_l2_raw` | Current L2 text baseline. |
| `api_doc_structured_header` | Path/symbol/signature/kind header + code body. |
| `api_doc_l1_plus_l2` | L1 graph summary + L2 code body. |
| `api_doc_symbols_first` | Repeat/privilege path, symbol, signature before body. |
| `api_doc_problem_terms_header` | Add normalized query terms as field labels only at query time, not snippet time. |

Why this is supported:

- Embeddings compare the relatedness of input strings. If the important code
  semantics are hidden in raw syntax, structured natural-language-ish fields
  can make the representation easier for the fixed model.
- OpenAI allows long enough inputs for these structured snippets, but we still
  need to cap body length to avoid drowning path/symbol information.

### 2. Query Formatting And Expansion

The query string is also an embedding input. We can improve the fixed API model
without changing the model by making the query look more like the document.

Candidate query documents:

| variant | description |
|---|---|
| `api_query_raw` | Raw user/grep query. |
| `api_query_code_search_intent` | `task: find code snippet relevant to ...` wrapper. |
| `api_query_identifier_split` | Split camel/snake identifiers and include original. |
| `api_query_scope_aware` | Include grep path/command scope if available. |
| `api_query_issue_trimmed` | Include only extracted issue keywords, not full issue body. |
| `api_query_multi_view_rrf` | Embed multiple query views and RRF their rankings. |

Our current canonical result already shows this matters:

```text
query_plus_legacy_scope Top5 = 0.5644
baseline_embedding_proxy Top5 = 0.4851
```

The mistake would be treating this as a new model. It is really query/document
formatting for the same route.

### 3. Field-Level API Embeddings

Instead of one embedding per snippet, embed fields separately:

```text
path_vector
symbol_vector
signature_vector
l1_graph_vector
body_vector
```

Then combine query similarities:

```text
score =
  w_path      * dot(q, path)
+ w_symbol    * dot(q, symbol)
+ w_signature * dot(q, signature)
+ w_l1_graph  * dot(q, l1_graph)
+ w_body      * dot(q, body)
```

Variants to test:

| variant | description |
|---|---|
| `api_field_weighted_static` | Static weights; start from symbol/path-heavy. |
| `api_field_max` | Use max field similarity, good for exact symbol/path matches. |
| `api_field_rrf` | Rank per field, then RRF field rankings. |
| `api_field_two_stage` | Field max chooses candidates, weighted sum reranks. |

Why this fits the current API:

- We can batch all field strings in one embeddings request.
- Snippet field vectors can be cached at index/build time.
- Query vector is computed once or a few times per search.

### 4. Chunking And Length Control

Embedding long code bodies can bury the small target signal. We should test
different L2 body views with the same API model.

Variants:

| variant | description |
|---|---|
| `api_body_signature_plus_first_n` | Header + signature + first N lines. |
| `api_body_identifier_summary` | Header + extracted identifiers/calls/imports + small code body. |
| `api_body_sliding_windows` | Split large class/function into windows; max/rrf over windows. |
| `api_body_docstring_stripped` | Remove comments/docstrings for identifier-heavy queries. |
| `api_body_comments_kept` | Keep docstrings/comments for natural-language queries. |

Expected behavior:

- Identifier queries likely prefer shorter symbol-heavy docs.
- Natural-language bug reports may prefer comments/docstrings/body context.
- Large classes should not be embedded as one giant body if the target is a
  small method/attribute.

### 5. Multi-Vector Per Snippet

This is the API-friendly version of late interaction. We cannot get token-level
vectors from the embedding API, but we can create multiple vectors per snippet:

```text
snippet vectors:
  path+symbol
  signature
  l1 graph
  body summary
  body window 1
  body window 2
```

Score:

```text
snippet_score = max_j dot(query_vector, snippet_vector_j)
```

or:

```text
snippet_score = RRF(rank(path_symbol), rank(signature), rank(l1), rank(body_windows))
```

Variants:

| variant | description |
|---|---|
| `api_multivector_max` | Max over per-snippet field/window vectors. |
| `api_multivector_rrf` | RRF over per-field rankings. |
| `api_multivector_weighted_max` | Max, but path/symbol/signature have boosts. |
| `api_multivector_l1_body` | Separate L1 graph vector and L2 body vector. |

This is likely the most realistic replacement for ColBERT under the fixed API.
With the cheaper default, start with `text-embedding-3-small` and only retry
`text-embedding-3-large` for the final best variant if budget allows.

### 6. Dimensionality And Cost Tuning

For `text-embedding-3` models, the API supports a `dimensions` parameter.

Variants:

| variant | description |
|---|---|
| `api_dim_1536` | Full `text-embedding-3-small` default dimension. |
| `api_dim_1024` | Cheaper vector DB and dot product. |
| `api_dim_512` | Very cheap exploratory setting. |
| `api_dim_ablation` | Test whether lower dimensions hurt route Top5. |

This is not expected to improve accuracy, but it may reduce latency/cost enough
to allow multi-vector indexing.

### 7. Score Calibration With The Same Embeddings

Even with the same embedding score, final route output can improve by
calibrating embedding scores against code-specific fields.

Variants:

| variant | description |
|---|---|
| `api_dense_plus_path_overlap` | Dense similarity + path/query token overlap. |
| `api_dense_plus_symbol_overlap` | Dense similarity + symbol/query overlap. |
| `api_dense_plus_l1_relation_overlap` | Dense similarity + L1 relation-name overlap. |
| `api_dense_rank_rrf_lexical` | RRF of dense rank + lexical field ranks. |

This keeps the route named "embedding", but accepts that code search needs
identifier exactness as a calibration signal.

## Updated First Experiment Set

Given the fixed API model constraint, test these before external model swaps:

| priority | variant | reason |
|---:|---|---|
| 1 | `api_doc_structured_header` | Cheapest, likely high impact. |
| 2 | `api_query_identifier_split` | Fixes code identifier tokenization mismatch. |
| 3 | `api_field_weighted_static` | Field weighting already helped in lexical proxy. |
| 4 | `api_field_rrf` | Robust if different fields win different searches. |
| 5 | `api_multivector_max` | API-friendly late interaction approximation. |
| 6 | `api_multivector_rrf` | More stable than max if fields are noisy. |
| 7 | `api_dense_rank_rrf_lexical` | Salvages exact code signals without changing model. |
| 8 | `api_dim_ablation` | Cost/latency tuning after quality improves. |

## First Fixed-API Experiment Attempt

Script:

```text
artifacts/api-embedding-exp/api_embedding_variants.py
```

The script implements five variants using the current OpenAI-compatible API
shape:

| variant | idea |
|---|---|
| `api_structured_raw_query` | Structured snippet document + raw query wrapper. |
| `api_structured_identifier_query` | Structured snippet document + identifier-split query. |
| `api_identifier_summary` | Identifier/call/path summary document + identifier-split query. |
| `api_scope_query` | Structured snippet document + query plus grep path/scope. |
| `api_field_rrf` | Field-level rankings over path/symbol, signature, and identifier summary, then RRF. |

Default mapping:

| variant | relationship to current production |
|---|---|
| `api_l2_raw_query` | True current production shape: raw query embedding vs current L2 `content.md` text with code-location header. Not yet implemented in this experiment script as a named variant. |
| `api_structured_raw_query` | Closest implemented variant to the current default. It still uses raw query, but makes snippet fields like path/symbol/signature explicit, so it is a slightly cleaner document format than production. |
| `api_structured_identifier_query` | New query-formatting experiment. |
| `api_identifier_summary` | New document-formatting experiment. |
| `api_scope_query` | New query-formatting experiment that uses grep path/scope context. |
| `api_field_rrf` | New multi-field/multi-vector ranking experiment. |

Actual API run status:

```text
blocked: embedding endpoint returned HTTP 403 insufficient_balance
```

The endpoint and key are present, but the proxy account has negative/insufficient
balance. The script is ready to run once the account is recharged:

```bash
python artifacts/api-embedding-exp/api_embedding_variants.py \
  --backend api \
  --dimensions 512 \
  --max-snippets 200
```

Because the API run was blocked, I ran the same five variants with the local
lexical proxy backend as a dry-run only. This verifies the benchmark wiring and
gives directional signal, but it is **not** the final API embedding result.

Dry-run settings:

```text
backend: proxy
model label: text-embedding-3-small
dimensions label: 512
usable_records: 101
candidate_limit: 80
max_snippets_per_record: 200
candidate_recall: 0.9307
```

Dry-run results:

| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count |
|---|---:|---:|---:|---:|---:|---:|
| `api_scope_query` | 0.3564 | 0.4752 | 0.5545 | 36 | 48 | 56 |
| `api_structured_raw_query` | 0.2475 | 0.3762 | 0.5050 | 25 | 38 | 51 |
| `api_structured_identifier_query` | 0.2277 | 0.3564 | 0.4752 | 23 | 36 | 48 |
| `api_identifier_summary` | 0.3267 | 0.4554 | 0.4554 | 33 | 46 | 46 |
| `api_field_rrf` | 0.3267 | 0.4158 | 0.4554 | 33 | 42 | 46 |

Dry-run interpretation:

- Scope/path-aware query formatting remains the strongest signal.
- Structured documents beat identifier-only summaries on Top5 in this proxy.
- Identifier summary improves Top1 but hurts Top5, suggesting it is better as a
  reranking feature than as the whole embedding document.
- Field RRF was not helpful with this lexical proxy, but the real API model may
  behave differently because field vectors are semantic rather than token-count
  based.

Next real API run after balance is fixed:

```text
1. Run max_snippets=200, dimensions=512 to validate behavior/cost.
2. Rerun best 2 variants at max_snippets=500.
3. Rerun best variant at dimensions=1536 or 3072.
```

Evaluation rule:

```text
full grep candidate pool
-> fixed API embedding variant ranks snippets independently
-> route Top1 / Top3 / Top5
```

Main target:

```text
Beat embedding route Top5 = 0.5644 if scope/path is allowed.
Beat pure query/snippet Top5 = 0.4950 if scope/path is not allowed.
```

## Implementation Notes For RTC

Use build-time caching:

```text
snippet_id -> field_name -> embedding vector
```

Recommended cache keys:

```text
model
dimensions
field_name
hash(field_text)
```

Batch API inputs:

```text
[
  "path+symbol text",
  "signature text",
  "l1 graph text",
  "body window 1",
  ...
]
```

Online query path:

```text
1. Build one or more query views.
2. Embed query views once.
3. Dot product against cached snippet field vectors.
4. Aggregate per variant.
5. Return embedding route top5/topK.
```

Avoid:

- Re-embedding all snippets at query time.
- Full issue body in the embedding query.
- Giant raw code chunks with weak/no field header.
- Treating the generic embedding API model as if it were a code-specific reranker.

## Previous Research Directions Deferred

The following remain interesting but are not first-line work while API model is
fixed:

### 1. Code-Specialized Dense Bi-Encoder

Examples:

- CodeBERT
- GraphCodeBERT
- UniXcoder
- CodeT5 / CodeT5+
- commercial code embedding models such as `voyage-code-3`

Idea:

```text
encode(query) dot encode(snippet_doc)
```

Snippet document should be structured:

```text
path: ...
symbol: ...
signature: ...
relations: ...
code: ...
```

Why it may help:

- CodeBERT was built for bimodal natural-language/programming-language
  representation and evaluated on code search.
- GraphCodeBERT adds data-flow structure, which is relevant for code semantics.
- UniXcoder uses cross-modal pretraining for code representation.
- Code-specific production models such as Voyage Code are optimized directly for
  code retrieval rather than generic semantic text search.

References:

- CodeBERT: https://arxiv.org/abs/2002.08155
- Microsoft CodeBERT / GraphCodeBERT / UniXcoder repo: https://github.com/microsoft/CodeBERT
- GraphCodeBERT: https://arxiv.org/abs/2009.08366
- UniXcoder: https://arxiv.org/abs/2203.03850
- CodeT5: https://arxiv.org/abs/2109.00859
- Salesforce CodeT5 repo: https://github.com/salesforce/CodeT5
- Voyage Code 3 model card: https://huggingface.co/voyageai/voyage-code-3

Candidate variants to test:

| variant | description |
|---|---|
| `dense_codebert_structured_doc` | CodeBERT embedding over structured snippet doc. |
| `dense_graphcodebert_structured_doc` | GraphCodeBERT embedding; include relation/data-flow-like text fields. |
| `dense_unixcoder_structured_doc` | UniXcoder embedding over query and snippet doc. |
| `dense_codet5_structured_doc` | CodeT5 encoder embedding if local model is feasible. |
| `dense_voyage_code_doc` | API/model embedding using a code-specialized model if allowed. |

### 2. Fielded Dense Retrieval

Idea:

Embed fields separately and combine:

```text
score =
  w_path      * sim(query, path)
+ w_symbol    * sim(query, symbol)
+ w_signature * sim(query, signature)
+ w_l1_graph  * sim(query, L1 graph doc)
+ w_body      * sim(query, code body)
```

Why it may help:

- Our canonical result already says field weighting helps:
  `field_weighted_embedding` Top5 `0.4950` vs baseline `0.4851`.
- Code snippets are not natural paragraphs. Symbol/signature/path are often much
  denser signals than body text.

Candidate variants:

| variant | description |
|---|---|
| `dense_field_weighted_static` | Fixed field weights tuned on current dataset. |
| `dense_field_max` | Score is max over fields, useful when one field exactly names target. |
| `dense_field_rrf` | Rank each field independently, then RRF field ranks. |
| `dense_field_path_symbol_first` | Heavily weight path/symbol/signature, body only as tie-breaker. |

### 3. Late-Interaction Retrieval

Reference:

- ColBERT: https://arxiv.org/abs/2004.12832
- ColBERT repo: https://github.com/stanford-futuredata/ColBERT

Idea:

Instead of compressing snippet/query into one vector, keep token vectors and
score by per-query-token max similarity:

```text
score(q, d) = sum_i max_j sim(q_i, d_j)
```

Why it may help:

- Code queries often contain a few critical tokens.
- Our `late_interaction_proxy` improved Top3 but not Top5, suggesting the idea
  has ranking value but our proxy is too weak.
- Real ColBERT-style token embeddings may improve route recall more than the
  current lexical proxy.

Candidate variants:

| variant | description |
|---|---|
| `colbert_code_tokens` | Real late interaction over query/snippet token embeddings. |
| `colbert_fields` | Late interaction per field, then weighted sum/RRF. |
| `late_interaction_identifier_boost` | Boost matches on symbol/signature/path tokens. |
| `late_interaction_l1_graph_boost` | Include L1 graph relation text as a field. |

### 4. Learned Sparse Embedding / SPLADE-Code

References:

- SPLADE: https://arxiv.org/abs/2107.05720
- SPLADE v2: https://arxiv.org/abs/2109.10086
- SPLADE repo: https://github.com/naver/splade
- SPLADE-Code: https://arxiv.org/abs/2603.22008

Idea:

Learn sparse query/document expansion weights, then use inverted-index style
matching:

```text
score = sparse_dot(query_expansion, snippet_expansion)
```

Why it may help:

- Code search needs exact token precision and semantic expansion.
- SPLADE-Code is specifically about learned sparse retrieval for code search.
- It may bridge the gap between BM25 and dense embeddings while remaining fast.

Candidate variants:

| variant | description |
|---|---|
| `splade_code_query_snippet` | Learned sparse score over structured snippet doc. |
| `splade_code_fields` | Field-specific sparse expansion, weighted by field. |
| `splade_code_hybrid_bm25f` | Combine SPLADE-Code with BM25F route score. |

### 5. Hybrid Dense + Sparse Embedding Route

Idea:

Treat embedding route as semantic route, but do not force it to be pure dense:

```text
embedding_route_score =
  a * dense_code_score
+ b * learned_sparse_score
+ c * fielded_dense_score
```

Why it may help:

- Dense catches semantic matches.
- Sparse catches exact identifiers and path names.
- The current dataset has many grep-like identifier queries, so pure semantic
  embeddings are likely underpowered.

Candidate variants:

| variant | description |
|---|---|
| `embedding_hybrid_dense_bm25f` | Dense code model plus BM25F as auxiliary. |
| `embedding_hybrid_dense_splade` | Dense code model plus SPLADE-Code. |
| `embedding_hybrid_dense_late` | Dense code model plus ColBERT-style MaxSim. |
| `embedding_hybrid_all_fields` | Dense + late interaction + sparse field scores. |

## Proposed First Experiment Set

Under the canonical metric, test:

| priority | variant | reason |
|---:|---|---|
| 1 | `dense_unixcoder_structured_doc` | Strong code-search-oriented open model family. |
| 2 | `dense_graphcodebert_structured_doc` | Adds code structure/data-flow prior. |
| 3 | `colbert_fields` | Real late interaction may fix weak proxy Top5. |
| 4 | `splade_code_fields` | Learned sparse may suit identifier-heavy code search. |
| 5 | `embedding_hybrid_dense_splade` | Best chance to combine semantic and exact matching. |
| 6 | `dense_field_rrf` | Cheap local fallback if model/API is unavailable. |

Evaluation rule:

```text
full grep candidate pool
-> embedding variant ranks snippets independently
-> measure route Top1 / Top3 / Top5
```

Success threshold:

```text
Beat current valid embedding route Top5 = 0.5644 if path/scope is allowed.
Beat current pure query/snippet embedding Top5 = 0.4950 if path/scope is not allowed.
```

## Production Constraint Notes

- If production `search_code` only receives `query`, avoid relying on
  `query_plus_legacy_scope`.
- If production can pass grep path/path-like constraints, path/scope should be
  represented explicitly as a query field.
- Real neural embedding experiments need caching. Re-embedding 500 snippets per
  query online will distort latency.
- For local/no-API experiments, start with model embeddings cached per snippet
  and query embeddings computed per search.
