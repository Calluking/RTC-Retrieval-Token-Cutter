# Final Rerank Experiments

Pipeline:

```text
grep candidate pool -> improved 4 route topK union -> final reranker -> top5
```

Improved routes:

- embedding: `query_plus_legacy_scope`
- bm25: `bm25f_symbol_heavy`
- symbol: `ctags_default`
- graph: `l1_relation_rrf`

## Settings

- usable_records: 101
- candidate_limit: 80
- max_snippets_per_record: 500
- candidate_recall: 0.9307
- avg_candidate_and_graph_build_sec: 0.413014
- avg_route_scoring_sec: 0.110906

## Union Recall

| route_top_k | union_recall |
|---:|---:|
| 1 | 0.5248 |
| 3 | 0.7030 |
| 5 | 0.8119 |

## Route TopK = 1

| reranker | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_rerank_time_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| weighted_sum_original | 0.3564 | 0.5248 | 0.5248 | 36 | 53 | 53 | 0.000025 |
| weighted_sum_balanced | 0.3564 | 0.5248 | 0.5248 | 36 | 53 | 53 | 0.000009 |
| weighted_sum_structural | 0.3564 | 0.5248 | 0.5248 | 36 | 53 | 53 | 0.000008 |
| rrf_equal | 0.3564 | 0.5248 | 0.5248 | 36 | 53 | 53 | 0.000007 |
| rrf_equal_plus_max | 0.3564 | 0.5248 | 0.5248 | 36 | 53 | 53 | 0.000007 |
| consensus_plus_max | 0.3564 | 0.5248 | 0.5248 | 36 | 53 | 53 | 0.000007 |
| rrf_weighted_route_top5 | 0.3465 | 0.5248 | 0.5248 | 35 | 53 | 53 | 0.000007 |
| rrf_weighted_structural | 0.3366 | 0.5248 | 0.5248 | 34 | 53 | 53 | 0.000008 |
| rrf_equal_plus_path_scope | 0.3366 | 0.5248 | 0.5248 | 34 | 53 | 53 | 0.000007 |
| salvaged_hybrid | 0.3366 | 0.5248 | 0.5248 | 34 | 53 | 53 | 0.000007 |
| max_route_score | 0.3168 | 0.5248 | 0.5248 | 32 | 53 | 53 | 0.000007 |
| graph_l1_rrf_only | 0.3366 | 0.4554 | 0.4554 | 34 | 46 | 46 | 0.000007 |
| late_interaction_only | 0.3267 | 0.4257 | 0.4257 | 33 | 43 | 43 | 0.000007 |
| bm25f_only | 0.3366 | 0.4158 | 0.4158 | 34 | 42 | 42 | 0.000006 |
| ctags_only | 0.3366 | 0.4158 | 0.4158 | 34 | 42 | 42 | 0.000006 |
| path_scoped_ctags_only | 0.3267 | 0.4059 | 0.4059 | 33 | 41 | 41 | 0.000006 |
| graph_bm25_ctags_rrf | 0.3366 | 0.3762 | 0.3762 | 34 | 38 | 38 | 0.000005 |

## Route TopK = 3

| reranker | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_rerank_time_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| rrf_weighted_structural | 0.3267 | 0.5050 | 0.6634 | 33 | 51 | 67 | 0.000015 |
| rrf_weighted_route_top5 | 0.3267 | 0.5050 | 0.6634 | 33 | 51 | 67 | 0.000014 |
| rrf_equal_plus_path_scope | 0.3267 | 0.4950 | 0.6535 | 33 | 50 | 66 | 0.000014 |
| salvaged_hybrid | 0.3267 | 0.4950 | 0.6535 | 33 | 50 | 66 | 0.000014 |
| max_route_score | 0.2970 | 0.5347 | 0.6436 | 30 | 54 | 65 | 0.000015 |
| rrf_equal | 0.3366 | 0.5446 | 0.6337 | 34 | 55 | 64 | 0.000015 |
| weighted_sum_structural | 0.3762 | 0.5149 | 0.6337 | 38 | 52 | 64 | 0.000015 |
| weighted_sum_balanced | 0.3564 | 0.5149 | 0.6337 | 36 | 52 | 64 | 0.000017 |
| weighted_sum_original | 0.3663 | 0.5050 | 0.6337 | 37 | 51 | 64 | 0.000026 |
| consensus_plus_max | 0.3366 | 0.5545 | 0.6238 | 34 | 56 | 63 | 0.000014 |
| rrf_equal_plus_max | 0.3366 | 0.5446 | 0.6238 | 34 | 55 | 63 | 0.000014 |
| graph_bm25_ctags_rrf | 0.3168 | 0.5149 | 0.6139 | 32 | 52 | 62 | 0.000012 |
| graph_l1_rrf_only | 0.3366 | 0.5050 | 0.6040 | 34 | 51 | 61 | 0.000015 |
| ctags_only | 0.3267 | 0.4950 | 0.6040 | 33 | 50 | 61 | 0.000014 |
| path_scoped_ctags_only | 0.3168 | 0.4950 | 0.5941 | 32 | 50 | 60 | 0.000013 |
| late_interaction_only | 0.2871 | 0.4950 | 0.5941 | 29 | 50 | 60 | 0.000015 |
| bm25f_only | 0.3366 | 0.5050 | 0.5842 | 34 | 51 | 59 | 0.000015 |

## Route TopK = 5

| reranker | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_rerank_time_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| rrf_equal | 0.3267 | 0.5149 | 0.6931 | 33 | 52 | 70 | 0.000016 |
| consensus_plus_max | 0.3465 | 0.5149 | 0.6733 | 35 | 52 | 68 | 0.000015 |
| rrf_equal_plus_max | 0.3267 | 0.5149 | 0.6733 | 33 | 52 | 68 | 0.000015 |
| max_route_score | 0.3069 | 0.5644 | 0.6535 | 31 | 57 | 66 | 0.000016 |
| bm25f_only | 0.3366 | 0.5050 | 0.6337 | 34 | 51 | 64 | 0.000017 |
| graph_l1_rrf_only | 0.3366 | 0.5050 | 0.6337 | 34 | 51 | 64 | 0.000017 |
| salvaged_hybrid | 0.3465 | 0.5248 | 0.6238 | 35 | 53 | 63 | 0.000015 |
| rrf_equal_plus_path_scope | 0.3267 | 0.5248 | 0.6238 | 33 | 53 | 63 | 0.000015 |
| weighted_sum_balanced | 0.3366 | 0.5149 | 0.6238 | 34 | 52 | 63 | 0.000017 |
| rrf_weighted_structural | 0.3267 | 0.5149 | 0.6238 | 33 | 52 | 63 | 0.000016 |
| rrf_weighted_route_top5 | 0.3267 | 0.5050 | 0.6238 | 33 | 51 | 63 | 0.000015 |
| graph_bm25_ctags_rrf | 0.3267 | 0.5050 | 0.6238 | 33 | 51 | 63 | 0.000015 |
| path_scoped_ctags_only | 0.3168 | 0.4851 | 0.6238 | 32 | 49 | 63 | 0.000015 |
| weighted_sum_structural | 0.3762 | 0.5149 | 0.6139 | 38 | 52 | 62 | 0.000015 |
| ctags_only | 0.3267 | 0.5248 | 0.6040 | 33 | 53 | 61 | 0.000016 |
| late_interaction_only | 0.3069 | 0.5149 | 0.5842 | 31 | 52 | 59 | 0.000016 |
| weighted_sum_original | 0.3564 | 0.4950 | 0.5743 | 36 | 50 | 58 | 0.000027 |
