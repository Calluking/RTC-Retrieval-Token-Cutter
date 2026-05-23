# L1 Relation Memory Traversal Trials

This retry tests the graph route as relation-memory traversal, not as a graph
rebuilt from already returned top5 snippets.

## Scope

Dataset:

```text
artifacts/legacy-search-dataset/search_targets.jsonl
```

Experiment scope:

```text
grep_candidate_pool_then_resolved_l1_relation_memory_traversal
```

The evaluator rebuilds the grep candidate pool, creates L1-style resolved
relations for each snippet, then scores snippets by walking those stored
relations.

The production L1 shape this mirrors is:

```text
graph.resolved_relations: calls:name -> path:start-end (uri);
                          extends:name -> path:start-end (uri);
                          contains:name -> path:start-end (uri)
```

Benchmark settings:

```text
usable_records: 101
candidate_limit: 80
max_snippets_per_record: 500
candidate_recall: 0.9307
records_with_resolved_l1_relations: 101
avg_resolved_l1_relations: 4128.44
```

## Methods

| variant | Relation-Memory Method | Main Reference |
|---|---|---|
| `l1_relation_1hop` | Query anchors from ctags/symbol match, then one hop over resolved L1 `calls`, `extends`, and `contains` edges. | Yamaguchi et al., *Modeling and Discovering Vulnerabilities with Code Property Graphs*; Horwitz et al., *Interprocedural Slicing Using Dependence Graphs*. |
| `l1_relation_2hop_decay` | Same as 1-hop, but allows two relation hops with stronger decay. | Crestani, *Application of Spreading Activation Techniques in Information Retrieval*. |
| `l1_query_gated_walk` | Two-hop walk, but reached nodes are discounted unless they still contain query evidence. | Haveliwala, *Topic-Sensitive PageRank*; Crestani spreading activation survey. |
| `l1_relation_pagerank` | Personalized PageRank over resolved L1 relation edges, seeded by query anchors. | Page et al., *The PageRank Citation Ranking*; Haveliwala, *Topic-Sensitive PageRank*. |
| `l1_relation_rrf` | Reciprocal Rank Fusion of direct anchor rank, 1-hop relation walk, and relation PageRank. | Cormack et al., *Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods*. |

## Recommended Variant

`l1_relation_rrf` is the best graph-memory variant in this benchmark. It keeps
the query anchor as the primary signal, then adds relation memory only as
additional ranked evidence:

```text
RRF(anchor_symbol_rank, l1_1hop_relation_rank, small_l1_pagerank_rank)
```

The supporting paper is Cormack et al.'s Reciprocal Rank Fusion work. The reason
it fits this route is that the three graph-memory signals are useful but noisy
in different ways; RRF rewards snippets that appear high in more than one list
without letting a single noisy graph traversal dominate.

## References

| Work | Used For |
|---|---|
| Yamaguchi et al., *Modeling and Discovering Vulnerabilities with Code Property Graphs* | Calls/contains/type-like relation graph for code. |
| Horwitz et al., *Interprocedural Slicing Using Dependence Graphs* | Relation traversal across program dependence/call structure. |
| Page et al., *The PageRank Citation Ranking* | Graph walk ranking. |
| Haveliwala, *Topic-Sensitive PageRank* | Query/topic-biased graph ranking. |
| Crestani, *Application of Spreading Activation Techniques in Information Retrieval* | Decayed query activation over a relation network. |
| Cormack et al., *Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods* | Robust fusion of multiple retrieval rankings. |
| Luan et al., *Aroma: Code Recommendation via Structural Code Search* | Structural code search using lightweight program features. |
| Allamanis et al., *Learning to Represent Programs with Graphs* | Program graph edges as retrieval/representation signal. |
| Gu et al., *Deep Code Search* | Query-to-code retrieval framing. |
| GraphCodeBERT | Code representation using structural data-flow edges. |

Links:

- Code Property Graphs: https://ieeexplore.ieee.org/document/6956581
- Program dependence graphs: https://dl.acm.org/doi/10.1145/24039.24041
- PageRank: http://ilpubs.stanford.edu:8090/422/
- Topic-Sensitive PageRank: https://dl.acm.org/doi/10.1145/511446.511513
- Spreading activation survey: https://dl.acm.org/doi/10.1016/0306-4573%2897%2900070-7
- Reciprocal Rank Fusion: https://dl.acm.org/doi/10.1145/1571941.1572114
- Aroma: https://dl.acm.org/doi/10.1145/3180155.3180224
- Learning to Represent Programs with Graphs: https://arxiv.org/abs/1711.00740
- Deep Code Search: https://dl.acm.org/doi/10.1145/3097983.3098013
- GraphCodeBERT: https://arxiv.org/abs/2009.08366

## Results

| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count |
|---|---:|---:|---:|---:|---:|---:|
| l1_relation_rrf | 0.3366 | 0.5050 | 0.6337 | 34 | 51 | 64 |
| l1_relation_2hop_decay | 0.3366 | 0.4950 | 0.6139 | 34 | 50 | 62 |
| l1_query_gated_walk | 0.3366 | 0.4950 | 0.6139 | 34 | 50 | 62 |
| l1_relation_1hop | 0.3366 | 0.4950 | 0.5743 | 34 | 50 | 58 |
| l1_relation_pagerank | 0.2079 | 0.3762 | 0.5644 | 21 | 38 | 57 |

## Result With Paper Mapping

| variant | top1 | top3 | top5 | paper / method family |
|---|---:|---:|---:|---|
| `l1_relation_rrf` | 0.3366 | 0.5050 | 0.6337 | Cormack et al., Reciprocal Rank Fusion. |
| `l1_relation_2hop_decay` | 0.3366 | 0.4950 | 0.6139 | Crestani, spreading activation for IR. |
| `l1_query_gated_walk` | 0.3366 | 0.4950 | 0.6139 | Topic-sensitive PageRank plus focused spreading activation. |
| `l1_relation_1hop` | 0.3366 | 0.4950 | 0.5743 | Code Property Graphs and Program Dependence Graph traversal. |
| `l1_relation_pagerank` | 0.2079 | 0.3762 | 0.5644 | PageRank / Topic-Sensitive PageRank. |

## Interpretation

- This is the graph design that actually matches L1 memory: anchor first, then
  traverse resolved relation targets.
- `l1_relation_rrf` is best overall: Top5 `0.6337`, better than the previous
  graph proxy Top5 `0.5842`.
- Pure PageRank is bad as a standalone ranker; it drifts away from the query.
- Relation walk helps when it is fused with the direct anchor, not when it
  replaces the anchor.
- Two-hop traversal helps Top5, but it must decay. Uncontrolled BFS is too noisy.

Recommended production direction:

```text
graph_score = RRF(anchor_symbol_rank, l1_1hop_relation_rank, small_l1_pagerank_rank)
```

Keep relation traversal as a route candidate generator/reranker, not as a broad
repo-wide random walk.
