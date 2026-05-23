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
- avg_candidate_and_graph_build_sec: 0.512645
- avg_route_scoring_sec: 0.135468

## Union Recall

| route_top_k | union_recall |
|---:|---:|
| 1 | 0.5149 |
| 3 | 0.6931 |
| 5 | 0.8020 |

## Route TopK = 1

| reranker | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_rerank_time_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| max_route_score | 0.3960 | 0.5149 | 0.5149 | 40 | 52 | 52 | 0.000008 |
| weighted_sum_original | 0.3564 | 0.5149 | 0.5149 | 36 | 52 | 52 | 0.000037 |
| weighted_sum_balanced | 0.3564 | 0.5149 | 0.5149 | 36 | 52 | 52 | 0.000010 |
| weighted_sum_structural | 0.3465 | 0.5149 | 0.5149 | 35 | 52 | 52 | 0.000010 |
| rrf_equal | 0.3465 | 0.5149 | 0.5149 | 35 | 52 | 52 | 0.000009 |
| rrf_weighted_structural | 0.3366 | 0.5149 | 0.5149 | 34 | 52 | 52 | 0.000008 |
| graph_l1_rrf_only | 0.3366 | 0.4455 | 0.4455 | 34 | 45 | 45 | 0.000007 |
| late_interaction_only | 0.3267 | 0.4158 | 0.4158 | 33 | 42 | 42 | 0.000008 |
| ctags_only | 0.3366 | 0.4059 | 0.4059 | 34 | 41 | 41 | 0.000008 |
| salvaged_hybrid | 0.3366 | 0.4059 | 0.4059 | 34 | 41 | 41 | 0.000007 |
| bm25f_only | 0.3267 | 0.4059 | 0.4059 | 33 | 41 | 41 | 0.000008 |

## Route TopK = 3

| reranker | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_rerank_time_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| max_route_score | 0.3663 | 0.5347 | 0.6436 | 37 | 54 | 65 | 0.000018 |
| rrf_weighted_structural | 0.3465 | 0.5050 | 0.6436 | 35 | 51 | 65 | 0.000018 |
| rrf_equal | 0.3564 | 0.5248 | 0.6337 | 36 | 53 | 64 | 0.000017 |
| salvaged_hybrid | 0.3267 | 0.5050 | 0.6238 | 33 | 51 | 63 | 0.000017 |
| weighted_sum_structural | 0.3168 | 0.5050 | 0.6139 | 32 | 51 | 62 | 0.000018 |
| weighted_sum_balanced | 0.3267 | 0.4950 | 0.6139 | 33 | 50 | 62 | 0.000020 |
| weighted_sum_original | 0.3366 | 0.4653 | 0.6139 | 34 | 47 | 62 | 0.000042 |
| ctags_only | 0.3465 | 0.4851 | 0.5842 | 35 | 49 | 59 | 0.000016 |
| graph_l1_rrf_only | 0.3366 | 0.5050 | 0.5743 | 34 | 51 | 58 | 0.000018 |
| late_interaction_only | 0.2871 | 0.4950 | 0.5743 | 29 | 50 | 58 | 0.000019 |
| bm25f_only | 0.3267 | 0.4653 | 0.5347 | 33 | 47 | 54 | 0.000017 |

## Route TopK = 5

| reranker | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_rerank_time_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| rrf_equal | 0.3168 | 0.5149 | 0.6733 | 32 | 52 | 68 | 0.000018 |
| max_route_score | 0.3663 | 0.5347 | 0.6634 | 37 | 54 | 67 | 0.000018 |
| graph_l1_rrf_only | 0.3366 | 0.5050 | 0.6337 | 34 | 51 | 64 | 0.000018 |
| rrf_weighted_structural | 0.3168 | 0.5050 | 0.6238 | 32 | 51 | 63 | 0.000019 |
| salvaged_hybrid | 0.3267 | 0.5149 | 0.6139 | 33 | 52 | 62 | 0.000018 |
| weighted_sum_balanced | 0.3366 | 0.5050 | 0.6139 | 34 | 51 | 62 | 0.000019 |
| weighted_sum_structural | 0.3267 | 0.5149 | 0.6040 | 33 | 52 | 61 | 0.000018 |
| ctags_only | 0.3267 | 0.4851 | 0.5941 | 33 | 49 | 60 | 0.000018 |
| bm25f_only | 0.3267 | 0.4752 | 0.5941 | 33 | 48 | 60 | 0.000019 |
| weighted_sum_original | 0.3465 | 0.4851 | 0.5842 | 35 | 49 | 59 | 0.000045 |
| late_interaction_only | 0.3069 | 0.5149 | 0.5743 | 31 | 52 | 58 | 0.000018 |
