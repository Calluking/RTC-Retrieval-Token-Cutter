# Graph Route Trials

These artifact-side trials test graph-route variants on the same offline
dataset used by the embedding, BM25, and symbol experiments.

## Scope

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

This means the experiment reranks the existing candidate union. It does not
rebuild full-repository graph recall.

Usable records:

```text
101
```

Candidate-union target recall:

```text
0.7327
```

## Variants

| variant | Query-To-Graph Idea | Research Basis |
|---|---|---|
| `graph_current_proxy` | Current graph proxy: lexical/symbol anchors plus same-file neighbor expansion. | Ctags-style symbol search plus local structural expansion. |
| `containment_expansion` | Anchor matching snippets, then expand through file/class/function containment edges. | Code Property Graphs and AST-style structural code representations. |
| `callgraph_expansion` | Anchor matching snippets, then expand through `calls` and `called_by` edges. | Call-graph based program comprehension and code navigation. |
| `import_expansion` | Use imports/package edges to connect query anchors to module-level neighbors. | Dependency graph / repository graph retrieval. |
| `inheritance_expansion` | Expand through `extends` and subclass/superclass edges. | Object-oriented program analysis and type hierarchy search. |
| `typed_weighted_bfs` | BFS with different weights for calls, imports, inheritance, containment, and nearby snippets. | Heterogeneous information networks and typed-edge retrieval. |
| `query_gated_bfs` | BFS expansion is discounted unless the neighbor still shares query terms. | Query-focused graph traversal / focused spreading activation. |
| `personalized_pagerank` | Seed the graph with query anchors and run restart-style PageRank. | PageRank, topic-sensitive PageRank, and personalized graph search. |
| `spreading_activation` | Iteratively pass activation from query anchors through graph edges with decay. | Spreading activation in semantic networks for information retrieval. |
| `graph_kernel_overlap` | Score a node by query overlap in its 1-hop neighborhood, like a small graph kernel. | Graph-kernel / neighborhood-subgraph similarity methods. |
| `path_package_graph` | Use path/package matches as anchors, then expand inside package/file hierarchy. | Repository hierarchy and package-dependency code search. |
| `hybrid_symbol_graph` | Weighted mixture of ctags, typed BFS, neighborhood overlap, and PageRank. | Learning-to-rank style feature fusion for code search. |

## References

| Work | Used For |
|---|---|
| Yamaguchi et al., *Modeling and Discovering Vulnerabilities with Code Property Graphs* | Typed AST/control/data/call graph representation of code. |
| Brin and Page, *The Anatomy of a Large-Scale Hypertextual Web Search Engine* | PageRank-style graph scoring. |
| Haveliwala, *Topic-Sensitive PageRank* | Personalized/topic-biased graph ranking. |
| Crestani, *Application of Spreading Activation Techniques in Information Retrieval* | Query-seeded graph activation with decay. |
| Vishwanathan et al., *Graph Kernels* | Neighborhood/subgraph similarity scoring. |
| Hellendoorn et al., *Deep Learning Type Inference* / program graph work | Program graphs with typed structural edges. |
| Allamanis et al., *Learning to Represent Programs with Graphs* | Graph neural representations using syntax/semantic edges. |
| Gu et al., *Deep Code Search* | Query-to-code search and feature/ranking framing. |
| Luan et al., *Aroma: Code Recommendation via Structural Code Search* | Structural code search over lightweight program features. |
| Kim et al., *FaCoY: A Code-to-Code Search Engine* | Query expansion and code-search reranking ideas. |

Links:

- Code Property Graphs: https://ieeexplore.ieee.org/document/6956581
- PageRank: http://ilpubs.stanford.edu:8090/422/
- Topic-Sensitive PageRank: https://dl.acm.org/doi/10.1145/511446.511513
- Spreading activation survey: https://dl.acm.org/doi/10.1016/0306-4573%2897%2900070-7
- Graph kernels survey: https://jmlr.org/papers/v11/vishwanathan10a.html
- Learning to Represent Programs with Graphs: https://arxiv.org/abs/1711.00740
- Deep Code Search: https://dl.acm.org/doi/10.1145/3097983.3098013
- Aroma: https://dl.acm.org/doi/10.1145/3180155.3180224
- FaCoY: https://dl.acm.org/doi/10.1145/3180155.3180170
- GraphCodeBERT: https://arxiv.org/abs/2009.08366

## Results

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

## Interpretation

- The current graph proxy is hard to beat on Top5 inside this candidate union.
- `personalized_pagerank` improves Top3 to `0.5248`, the best graph-route Top3.
- `import_expansion`, `path_package_graph`, and `containment_expansion` have the
  best Top1 among the variants at `0.3366`.
- Pure callgraph/BFS expansion is weak here. On this benchmark, the graph route
  really is mostly a symbol route with careful local expansion.
- A useful next production candidate is not broad BFS. It is a conservative
  graph score:

```text
max(current_graph_proxy, small_weight * personalized_pagerank)
```

or a final-rerank feature that adds PageRank only as a tie breaker.
