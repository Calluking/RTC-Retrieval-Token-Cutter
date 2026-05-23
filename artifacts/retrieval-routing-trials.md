# Retrieval Routing Trials

This note consolidates the artifact-side routing experiments for the current
offline dataset. Production retrieval code was not changed by these trials.

## Dataset And Scope

Dataset:

```text
artifacts/legacy-search-dataset/search_targets.jsonl
```

Source predictions:

```text
artifacts/retrieval-eval/predictions.jsonl
```

Experiment scope:

```text
rerank_existing_4_route_top5_union
```

The experiments rerank the existing candidate union from the current four-route
retriever. They measure whether alternative scoring functions improve ordering
inside the candidate pool.

Usable records:

```text
101
```

## Embedding Route Trials

Reference ideas:

| Work | Used For |
|---|---|
| CodeSearchNet: *Evaluating the State of Semantic Code Search* | NL-code retrieval and query/code vocabulary mismatch. |
| CodeBERT: *A Pre-Trained Model for Programming and Natural Languages* | Code-specific dense retrieval representations. |
| GraphCodeBERT: *Pre-training Code Representations with Data Flow* | Code-aware embeddings with structural/data-flow information. |
| ColBERT: *Efficient and Effective Passage Search via Contextualized Late Interaction over BERT* | Late interaction / MaxSim-style token matching. |
| HyDE: *Precise Zero-Shot Dense Retrieval without Relevance Labels* | Query expansion / hypothetical-document-style dense retrieval. |

Links:

- CodeSearchNet: https://arxiv.org/abs/1909.09436
- CodeBERT: https://arxiv.org/abs/2002.08155
- GraphCodeBERT: https://arxiv.org/abs/2009.08366
- ColBERT: https://arxiv.org/abs/2004.12832
- HyDE: https://arxiv.org/abs/2212.10496

Results:

| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count |
|---|---:|---:|---:|---:|---:|---:|
| query_plus_issue | 0.2376 | 0.4851 | 0.5743 | 24 | 49 | 58 |
| late_interaction_proxy | 0.2970 | 0.5050 | 0.5644 | 30 | 51 | 57 |
| query_plus_legacy_scope | 0.2871 | 0.4059 | 0.5149 | 29 | 41 | 52 |
| field_weighted_embedding | 0.2970 | 0.3960 | 0.5149 | 30 | 40 | 52 |
| baseline_embedding_proxy | 0.2178 | 0.3366 | 0.4752 | 22 | 34 | 48 |
| pseudo_relevance_feedback | 0.1782 | 0.2871 | 0.3960 | 18 | 29 | 40 |

Interpretation:

- `baseline_embedding_proxy` is the current/original embedding proxy.
- `late_interaction_proxy` is the best general-purpose embedding variant because
  it only needs query, path, symbol, signature, and body.
- `query_plus_issue` has the best Top5 in SWE because SWE provides a rich issue
  statement. It may not generalize outside SWE when no issue text exists.

## BM25 Route Trials

Reference ideas:

| Work | Used For |
|---|---|
| Robertson and Zaragoza, *The Probabilistic Relevance Framework: BM25 and Beyond* | BM25 and BM25F foundations. |
| BM25F / fielded BM25 | Treat structured documents as weighted fields. For code: symbol, signature, path, body. |
| Lv and Zhai, *Lower-Bounding Term Frequency Normalization* | BM25+ and BM25L; reduce over-penalizing long matching documents. |
| Language Modeling for IR with Dirichlet smoothing | Non-BM25 lexical baseline. |
| Trotman et al., *Improvements to BM25 and Language Models Examined* | Practical BM25 variants and parameter sensitivity. |

Links:

- BM25 and BM25F overview: https://doi.org/10.1561/1500000019
- BM25/BM25F Lucene implementation: https://arxiv.org/abs/0911.5046
- Lower-bounding TF normalization: https://timan.cs.illinois.edu/czhai/pub/cikm11-bm25.pdf
- Trotman et al.: https://dl.acm.org/doi/10.1145/2063576.2063584

Results:

| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count |
|---|---:|---:|---:|---:|---:|---:|
| bm25_tuned_short_code | 0.2673 | 0.4455 | 0.6139 | 27 | 45 | 62 |
| bm25f_code_fields | 0.2574 | 0.4950 | 0.5743 | 26 | 50 | 58 |
| bm25_plus | 0.2376 | 0.4257 | 0.5446 | 24 | 43 | 55 |
| bm25_l | 0.2376 | 0.4158 | 0.5347 | 24 | 42 | 54 |
| dirichlet_lm | 0.2673 | 0.4158 | 0.4851 | 27 | 42 | 49 |
| bm25_default | 0.2475 | 0.4059 | 0.4752 | 25 | 41 | 48 |

Interpretation:

- `bm25_default` is the original BM25 proxy.
- `bm25_tuned_short_code` is still BM25, but uses lower `k1` and lower `b`:

```text
default: k1 = 1.5, b = 0.75
tuned:   k1 = 0.9, b = 0.35
```

- Lower `k1` makes repeated terms saturate sooner.
- Lower `b` reduces the long-snippet penalty.
- This fits code snippets because chunks are already structured and a longer
  class/function is not automatically less relevant.
- `bm25f_code_fields` has the best Top3, suggesting field-aware lexical scoring
  is also promising.

## Symbol Route Trials

Reference ideas:

| Work/System | Used For |
|---|---|
| Ctags / Universal Ctags | Extract declarations: classes, functions, variables, methods, etc. |
| Sourcegraph symbol search / Zoekt | Practical code-search systems use symbol indexes and ctags-like signals. |
| Sourcerer / CodeRank | Structural source-code retrieval beyond plain text. |
| Identifier splitting work, including Lingua::IdSplitter and Spiral | Split `FileStoragePermissions` into `file`, `storage`, `permissions`. |
| Fuzzy matching / edit-distance matching | Partial, typo-like, and abbreviation-friendly symbol matching. |

Links:

- Sourcegraph symbol search: https://sourcegraph.com/docs/code-search/types/symbol
- Zoekt: https://github.com/sourcegraph/zoekt
- Sourcerer: https://link.springer.com/article/10.1007/s10618-008-0118-x
- Spiral identifier splitting: https://joss.theoj.org/papers/10.21105/joss.00653
- Source identifiers to natural language terms: https://www.sciencedirect.com/science/article/abs/pii/S0164121214002179

Results:

| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count |
|---|---:|---:|---:|---:|---:|---:|
| ctags_default | 0.3366 | 0.4851 | 0.5743 | 34 | 49 | 58 |
| ctags_plus_fuzzy | 0.3069 | 0.4950 | 0.5644 | 31 | 50 | 57 |
| ctags_plus_subtoken | 0.2871 | 0.4554 | 0.5644 | 29 | 46 | 57 |
| fuzzy_symbol | 0.2475 | 0.4653 | 0.5545 | 25 | 47 | 56 |
| all_symbol_features | 0.2574 | 0.3960 | 0.5545 | 26 | 40 | 56 |
| acronym_abbrev | 0.2376 | 0.3861 | 0.4950 | 24 | 39 | 50 |
| identifier_subtoken | 0.2574 | 0.3762 | 0.4851 | 26 | 38 | 49 |
| symbol_graph_neighbor | 0.2574 | 0.3663 | 0.4653 | 26 | 37 | 47 |
| kind_aware_symbol | 0.2574 | 0.3069 | 0.4653 | 26 | 31 | 47 |

Interpretation:

- `ctags_default` remains the strongest symbol route overall.
- `ctags_plus_fuzzy` slightly improves Top3 but hurts Top1 and Top5.
- Fuzzy/subtoken/abbreviation features should be auxiliary features, not a
  replacement for the current symbol score.

## Graph Route Trials

Reference ideas:

| Work/System | Used For |
|---|---|
| Code Property Graphs | Typed code graph with AST/control/data/call-style edges. |
| PageRank and Topic-Sensitive PageRank | Query-seeded graph ranking / personalized graph traversal. |
| Spreading activation for information retrieval | Decayed activation from query anchors through graph edges. |
| Graph kernels | Neighborhood/subgraph overlap as a similarity signal. |
| Learning to Represent Programs with Graphs | Typed program graph edges as code representation. |
| Aroma and FaCoY | Structural code search and query/code-search reranking. |

Links:

- Code Property Graphs: https://ieeexplore.ieee.org/document/6956581
- PageRank: http://ilpubs.stanford.edu:8090/422/
- Topic-Sensitive PageRank: https://dl.acm.org/doi/10.1145/511446.511513
- Spreading activation survey: https://dl.acm.org/doi/10.1016/0306-4573%2897%2900070-7
- Graph kernels survey: https://jmlr.org/papers/v11/vishwanathan10a.html
- Learning to Represent Programs with Graphs: https://arxiv.org/abs/1711.00740
- Aroma: https://dl.acm.org/doi/10.1145/3180155.3180224
- FaCoY: https://dl.acm.org/doi/10.1145/3180155.3180170
- GraphCodeBERT: https://arxiv.org/abs/2009.08366

Results:

| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count |
|---|---:|---:|---:|---:|---:|---:|
| graph_current_proxy | 0.3267 | 0.4950 | 0.5842 | 33 | 50 | 59 |
| hybrid_symbol_graph | 0.3168 | 0.4950 | 0.5842 | 32 | 50 | 59 |
| inheritance_expansion | 0.2673 | 0.4554 | 0.5842 | 27 | 46 | 59 |
| personalized_pagerank | 0.2970 | 0.5248 | 0.5743 | 30 | 53 | 58 |
| import_expansion | 0.3366 | 0.4950 | 0.5743 | 34 | 50 | 58 |
| path_package_graph | 0.3366 | 0.4851 | 0.5743 | 34 | 49 | 58 |
| graph_kernel_overlap | 0.2970 | 0.4950 | 0.5644 | 30 | 50 | 57 |
| containment_expansion | 0.3366 | 0.4752 | 0.5545 | 34 | 48 | 56 |
| spreading_activation | 0.2871 | 0.4158 | 0.5248 | 29 | 42 | 53 |
| query_gated_bfs | 0.2475 | 0.3861 | 0.4851 | 25 | 39 | 49 |
| callgraph_expansion | 0.2178 | 0.3465 | 0.4851 | 22 | 35 | 49 |
| typed_weighted_bfs | 0.2475 | 0.3762 | 0.4752 | 25 | 38 | 48 |

Interpretation:

- The current graph proxy is still strongest on Top5 inside the current
  candidate union.
- `personalized_pagerank` has the best graph Top3, so it may be useful as a
  small tie-breaker feature.
- Broad callgraph/BFS expansion performs poorly here. The data supports the
  concern that this graph route is mostly an expanded symbol route, and that
  expansion needs to stay conservative.

## L1 Relation Memory Trials

This retry uses the graph route as stored relation-memory traversal:

```text
query -> symbol/text anchors -> resolved L1 relations -> reached snippets
```

It mirrors the production L1 relation shape:

```text
graph.resolved_relations: calls:name -> path:start-end (uri);
                          extends:name -> path:start-end (uri);
                          contains:name -> path:start-end (uri)
```

Experiment scope:

```text
grep_candidate_pool_then_resolved_l1_relation_memory_traversal
```

Settings:

```text
usable_records: 101
candidate_limit: 80
max_snippets_per_record: 500
candidate_recall: 0.9307
records_with_resolved_l1_relations: 101
avg_resolved_l1_relations: 4128.44
```

Reference ideas:

| variant | Relation-Memory Method | Main Reference |
|---|---|---|
| `l1_relation_1hop` | Query anchors, then one hop over resolved L1 `calls`, `extends`, and `contains` edges. | Yamaguchi et al., *Modeling and Discovering Vulnerabilities with Code Property Graphs*; Horwitz et al., *Interprocedural Slicing Using Dependence Graphs*. |
| `l1_relation_2hop_decay` | Two-hop relation traversal with stronger decay. | Crestani, *Application of Spreading Activation Techniques in Information Retrieval*. |
| `l1_query_gated_walk` | Two-hop traversal, discounted unless reached snippets still match query evidence. | Haveliwala, *Topic-Sensitive PageRank*; Crestani spreading activation survey. |
| `l1_relation_pagerank` | Personalized PageRank over resolved L1 relation edges. | Page et al., *The PageRank Citation Ranking*; Haveliwala, *Topic-Sensitive PageRank*. |
| `l1_relation_rrf` | Reciprocal Rank Fusion of anchor rank, 1-hop relation rank, and small PageRank rank. | Cormack et al., *Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods*. |

Links:

- Code Property Graphs: https://ieeexplore.ieee.org/document/6956581
- Program dependence graphs: https://dl.acm.org/doi/10.1145/24039.24041
- PageRank: http://ilpubs.stanford.edu:8090/422/
- Topic-Sensitive PageRank: https://dl.acm.org/doi/10.1145/511446.511513
- Spreading activation survey: https://dl.acm.org/doi/10.1016/0306-4573%2897%2900070-7
- Reciprocal Rank Fusion: https://dl.acm.org/doi/10.1145/1571941.1572114

Results:

| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count |
|---|---:|---:|---:|---:|---:|---:|
| l1_relation_rrf | 0.3366 | 0.5050 | 0.6337 | 34 | 51 | 64 |
| l1_relation_2hop_decay | 0.3366 | 0.4950 | 0.6139 | 34 | 50 | 62 |
| l1_query_gated_walk | 0.3366 | 0.4950 | 0.6139 | 34 | 50 | 62 |
| l1_relation_1hop | 0.3366 | 0.4950 | 0.5743 | 34 | 50 | 58 |
| l1_relation_pagerank | 0.2079 | 0.3762 | 0.5644 | 21 | 38 | 57 |

Results with paper mapping:

| variant | top1 | top3 | top5 | paper / method family |
|---|---:|---:|---:|---|
| `l1_relation_rrf` | 0.3366 | 0.5050 | 0.6337 | Cormack et al., Reciprocal Rank Fusion. |
| `l1_relation_2hop_decay` | 0.3366 | 0.4950 | 0.6139 | Crestani, spreading activation for IR. |
| `l1_query_gated_walk` | 0.3366 | 0.4950 | 0.6139 | Topic-sensitive PageRank plus focused spreading activation. |
| `l1_relation_1hop` | 0.3366 | 0.4950 | 0.5743 | Code Property Graphs and Program Dependence Graph traversal. |
| `l1_relation_pagerank` | 0.2079 | 0.3762 | 0.5644 | PageRank / Topic-Sensitive PageRank. |

Interpretation:

- This is the more relevant graph experiment for our L1 design.
- `l1_relation_rrf` is best: it beats the previous graph proxy Top5
  `0.5842` with Top5 `0.6337`.
- `l1_relation_rrf` is now the recommended graph-memory route:

```text
RRF(anchor_symbol_rank, l1_1hop_relation_rank, small_l1_pagerank_rank)
```

- Relation traversal helps when fused with direct anchors.
- Pure PageRank drifts too far from the query and is weak by itself.
- Two-hop traversal helps Top5, but only with decay/gating.

## Current Recommendations

| Route | Recommendation |
|---|---|
| Embedding | Try `late_interaction_proxy` as the general-purpose replacement; use `query_plus_issue` only when strong task context exists. |
| BM25 | Try `bm25_tuned_short_code` first; then test `bm25f_code_fields` if we want a more code-aware lexical scorer. |
| Symbol | Keep `ctags_default`; optionally add a small fuzzy auxiliary feature in final fusion. |
| Graph | Prefer L1 relation-memory RRF: direct anchor rank + resolved 1-hop relation rank + small PageRank rank. |
