# Canonical Variant Benchmark

Metric:

```text
full grep candidate pool -> route variant ranks independently -> top1/top3/top5 hit
```

## Settings

- usable_records: 101
- candidate_limit: 80
- max_snippets_per_record: 500
- candidate_recall: 0.9307
- avg_snippets_per_search: 493.24

This is the canonical route-optimization metric. These are not rerank-union scores.

## embedding

| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_score_time_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| query_plus_legacy_scope | 0.3663 | 0.4950 | 0.5644 | 37 | 50 | 57 | 0.079135 |
| field_weighted_embedding | 0.3069 | 0.3960 | 0.4950 | 31 | 40 | 50 | 0.074859 |
| late_interaction_proxy | 0.2772 | 0.4455 | 0.4851 | 28 | 45 | 49 | 0.095184 |
| baseline_embedding_proxy | 0.2178 | 0.3366 | 0.4851 | 22 | 34 | 49 | 0.057985 |
| pseudo_relevance_feedback | 0.1584 | 0.2475 | 0.3069 | 16 | 25 | 31 | 0.130214 |
| query_plus_issue | 0.0891 | 0.1584 | 0.2277 | 9 | 16 | 23 | 0.089711 |

## bm25

| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_score_time_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| bm25f_code_fields | 0.3267 | 0.4653 | 0.5941 | 33 | 47 | 60 | 0.168785 |
| bm25_l | 0.2376 | 0.3861 | 0.4950 | 24 | 39 | 50 | 0.081901 |
| dirichlet_lm | 0.3168 | 0.4059 | 0.4752 | 32 | 41 | 48 | 0.068681 |
| bm25_tuned_short_code | 0.2970 | 0.4059 | 0.4752 | 30 | 41 | 48 | 0.066525 |
| bm25_default | 0.2277 | 0.3663 | 0.4752 | 23 | 37 | 48 | 0.065493 |
| bm25_plus | 0.2475 | 0.3762 | 0.4653 | 25 | 38 | 47 | 0.066719 |

## symbol

| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_score_time_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| ctags_default | 0.3366 | 0.4950 | 0.6040 | 34 | 50 | 61 | 0.001079 |
| ctags_plus_subtoken | 0.3366 | 0.4950 | 0.5941 | 34 | 50 | 60 | 0.019115 |
| ctags_plus_fuzzy | 0.3168 | 0.4950 | 0.5743 | 32 | 50 | 58 | 0.388866 |
| all_symbol_features | 0.3168 | 0.4554 | 0.5347 | 32 | 46 | 54 | 0.443108 |
| identifier_subtoken | 0.2772 | 0.3762 | 0.4752 | 28 | 38 | 48 | 0.018010 |
| kind_aware_symbol | 0.2772 | 0.3663 | 0.4653 | 28 | 37 | 47 | 0.018264 |
| fuzzy_symbol | 0.2475 | 0.4356 | 0.4554 | 25 | 44 | 46 | 0.385418 |
| acronym_abbrev | 0.2178 | 0.3465 | 0.4554 | 22 | 35 | 46 | 0.020281 |
| symbol_graph_neighbor | 0.2772 | 0.3663 | 0.4158 | 28 | 37 | 42 | 0.021574 |

## graph_memory

| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_score_time_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| l1_relation_rrf | 0.3366 | 0.5050 | 0.6337 | 34 | 51 | 64 | 0.053729 |
| l1_relation_2hop_decay | 0.3366 | 0.4950 | 0.6139 | 34 | 50 | 62 | 0.015623 |
| l1_query_gated_walk | 0.3366 | 0.4950 | 0.6139 | 34 | 50 | 62 | 0.125906 |
| l1_relation_1hop | 0.3366 | 0.4950 | 0.5743 | 34 | 50 | 58 | 0.007321 |
| l1_relation_pagerank | 0.2079 | 0.3762 | 0.5644 | 21 | 38 | 57 | 0.042933 |
