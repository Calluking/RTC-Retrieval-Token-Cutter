# Combined Route Benchmark

## Settings

- usable_records: 101
- candidate_limit: 80
- max_snippets_per_record: 500
- candidate_recall: 0.9307
- avg_snippets_per_search: 493.24
- fusion_weights: `{"embedding": 0.45, "bm25": 0.25, "ctags": 0.15, "graph": 0.15}`

Scope note: this is a full grep-candidate recompute benchmark. It is
not the same as the earlier per-route experiments that reranked only the
existing four-route top5 union, so those metrics should not be expected
to match exactly.

Route mapping:

- original: `{"embedding": "embedding_proxy", "bm25": "bm25_default", "ctags": "ctags_default", "graph": "graph_proxy"}`
- updated: `{"embedding": "late_interaction_proxy", "bm25": "bm25_tuned_short_code", "ctags": "ctags_default", "graph": "l1_relation_rrf"}`

## Original Routes

| route | top1 | top3 | top5 | top1_count | top3_count | top5_count |
|---|---:|---:|---:|---:|---:|---:|
| embedding | 0.2178 | 0.3366 | 0.4851 | 22 | 34 | 49 |
| bm25 | 0.2277 | 0.3663 | 0.4752 | 23 | 37 | 48 |
| ctags | 0.3366 | 0.4950 | 0.6040 | 34 | 50 | 61 |
| graph | 0.3267 | 0.5050 | 0.5842 | 33 | 51 | 59 |
| overall | 0.2673 | 0.3861 | 0.5545 | 27 | 39 | 56 |

## Updated Routes

| route | top1 | top3 | top5 | top1_count | top3_count | top5_count |
|---|---:|---:|---:|---:|---:|---:|
| embedding | 0.2772 | 0.4455 | 0.4851 | 28 | 45 | 49 |
| bm25 | 0.2970 | 0.4059 | 0.4752 | 30 | 41 | 48 |
| ctags | 0.3366 | 0.4950 | 0.6040 | 34 | 50 | 61 |
| graph | 0.3366 | 0.5050 | 0.6337 | 34 | 51 | 64 |
| overall | 0.2970 | 0.4851 | 0.5743 | 30 | 49 | 58 |

## Side-By-Side Deltas

| route | original_top1 | updated_top1 | delta_top1 | original_top3 | updated_top3 | delta_top3 | original_top5 | updated_top5 | delta_top5 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| embedding | 0.2178 | 0.2772 | +0.0594 | 0.3366 | 0.4455 | +0.1089 | 0.4851 | 0.4851 | +0.0000 |
| bm25 | 0.2277 | 0.2970 | +0.0693 | 0.3663 | 0.4059 | +0.0396 | 0.4752 | 0.4752 | +0.0000 |
| ctags | 0.3366 | 0.3366 | +0.0000 | 0.4950 | 0.4950 | +0.0000 | 0.6040 | 0.6040 | +0.0000 |
| graph | 0.3267 | 0.3366 | +0.0099 | 0.5050 | 0.5050 | +0.0000 | 0.5842 | 0.6337 | +0.0495 |
| overall | 0.2673 | 0.2970 | +0.0297 | 0.3861 | 0.4851 | +0.0990 | 0.5545 | 0.5743 | +0.0198 |

## Timing

| system | avg_search_total_sec | avg_candidate_build_sec | avg_memory_graph_build_sec | avg_embedding_sec | avg_bm25_sec | avg_ctags_sec | avg_graph_sec | avg_overall_rerank_sec |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| original | 0.948354 | 0.826273 | 0.000000 | 0.051688 | 0.060059 | 0.001028 | 0.007069 | 0.000598 |
| updated | 1.057226 | 0.826273 | 0.039067 | 0.084156 | 0.059359 | 0.001025 | 0.045089 | 0.000578 |

Timing note: `avg_search_total_sec` includes candidate/snippet building.
For the updated system it also includes L1 memory graph construction.
