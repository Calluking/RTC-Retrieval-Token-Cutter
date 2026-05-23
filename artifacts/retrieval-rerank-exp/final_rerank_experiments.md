# Final Rerank Experiments

Pipeline:

```text
grep candidate pool -> improved 4 route topK union -> final reranker -> top5
```

Improved routes:

- embedding: `query_plus_legacy_scope`
- bm25: `bm25f_code_fields`
- symbol: `ctags_default`
- graph: `l1_relation_rrf`

## Settings

- usable_records: 101
- candidate_limit: 80
- max_snippets_per_record: 500
- candidate_recall: 0.9307
- avg_candidate_and_graph_build_sec: 0.541480
- avg_route_scoring_sec: 0.139460

## Union Recall

| route_top_k | union_recall |
|---:|---:|
| 5 | 0.8020 |
| 10 | 0.8614 |
| 20 | 0.8812 |

## Route TopK = 5

| reranker | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_rerank_time_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| rrf_equal | 0.3168 | 0.5149 | 0.6733 | 32 | 52 | 68 | 0.000019 |
| max_route_score | 0.3762 | 0.5545 | 0.6634 | 38 | 56 | 67 | 0.000021 |
| graph_l1_rrf_only | 0.3366 | 0.5050 | 0.6337 | 34 | 51 | 64 | 0.000018 |
| rrf_weighted_structural | 0.3168 | 0.5050 | 0.6238 | 32 | 51 | 63 | 0.000018 |
| ctags_only | 0.3267 | 0.5347 | 0.6139 | 33 | 54 | 62 | 0.000018 |
| salvaged_hybrid | 0.3267 | 0.5149 | 0.6139 | 33 | 52 | 62 | 0.000019 |
| weighted_sum_balanced | 0.3366 | 0.5050 | 0.6139 | 34 | 51 | 62 | 0.000024 |
| weighted_sum_structural | 0.3267 | 0.5149 | 0.6040 | 33 | 52 | 61 | 0.000020 |
| bm25f_only | 0.3267 | 0.4653 | 0.5941 | 33 | 47 | 60 | 0.000021 |
| weighted_sum_original | 0.3465 | 0.4851 | 0.5842 | 35 | 49 | 59 | 0.000057 |
| late_interaction_only | 0.3069 | 0.5050 | 0.5743 | 31 | 51 | 58 | 0.000020 |

## Route TopK = 10

| reranker | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_rerank_time_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| max_route_score | 0.3564 | 0.5743 | 0.6436 | 36 | 58 | 65 | 0.000022 |
| graph_l1_rrf_only | 0.3366 | 0.5050 | 0.6337 | 34 | 51 | 64 | 0.000021 |
| salvaged_hybrid | 0.3069 | 0.4851 | 0.6337 | 31 | 49 | 64 | 0.000021 |
| weighted_sum_structural | 0.3267 | 0.5248 | 0.6238 | 33 | 53 | 63 | 0.000023 |
| rrf_equal | 0.3168 | 0.5248 | 0.6139 | 32 | 53 | 62 | 0.000021 |
| weighted_sum_balanced | 0.3366 | 0.5149 | 0.6139 | 34 | 52 | 62 | 0.000025 |
| rrf_weighted_structural | 0.3168 | 0.5149 | 0.6040 | 32 | 52 | 61 | 0.000020 |
| bm25f_only | 0.3267 | 0.4752 | 0.5941 | 33 | 48 | 60 | 0.000021 |
| weighted_sum_original | 0.3663 | 0.5050 | 0.5842 | 37 | 51 | 59 | 0.000050 |
| ctags_only | 0.3564 | 0.5248 | 0.5644 | 36 | 53 | 57 | 0.000021 |
| late_interaction_only | 0.2970 | 0.4653 | 0.5545 | 30 | 47 | 56 | 0.000020 |

## Route TopK = 20

| reranker | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_rerank_time_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| max_route_score | 0.3564 | 0.5743 | 0.6436 | 36 | 58 | 65 | 0.000027 |
| graph_l1_rrf_only | 0.3366 | 0.5050 | 0.6337 | 34 | 51 | 64 | 0.000027 |
| weighted_sum_structural | 0.3267 | 0.5248 | 0.6238 | 33 | 53 | 63 | 0.000026 |
| weighted_sum_balanced | 0.3366 | 0.5149 | 0.6139 | 34 | 52 | 62 | 0.000028 |
| rrf_weighted_structural | 0.3168 | 0.5149 | 0.6139 | 32 | 52 | 62 | 0.000027 |
| rrf_equal | 0.3168 | 0.5050 | 0.6139 | 32 | 51 | 62 | 0.000029 |
| salvaged_hybrid | 0.3168 | 0.4851 | 0.6139 | 32 | 49 | 62 | 0.000027 |
| bm25f_only | 0.3267 | 0.4752 | 0.5941 | 33 | 48 | 60 | 0.000027 |
| ctags_only | 0.3564 | 0.5446 | 0.5842 | 36 | 55 | 59 | 0.000026 |
| weighted_sum_original | 0.3564 | 0.4950 | 0.5743 | 36 | 50 | 58 | 0.000065 |
| late_interaction_only | 0.2970 | 0.4554 | 0.5149 | 30 | 46 | 52 | 0.000028 |
