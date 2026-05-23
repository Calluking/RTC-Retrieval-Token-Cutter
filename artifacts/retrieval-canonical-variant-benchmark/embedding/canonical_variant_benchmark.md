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
- avg_candidate_build_sec: 1.113882
- avg_memory_graph_build_sec: 0.000000

## embedding

| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_score_time_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| query_plus_legacy_scope | 0.3663 | 0.4950 | 0.5644 | 37 | 50 | 57 | 0.079135 |
| field_weighted_embedding | 0.3069 | 0.3960 | 0.4950 | 31 | 40 | 50 | 0.074859 |
| late_interaction_proxy | 0.2772 | 0.4455 | 0.4851 | 28 | 45 | 49 | 0.095184 |
| baseline_embedding_proxy | 0.2178 | 0.3366 | 0.4851 | 22 | 34 | 49 | 0.057985 |
| pseudo_relevance_feedback | 0.1584 | 0.2475 | 0.3069 | 16 | 25 | 31 | 0.130214 |
| query_plus_issue | 0.0891 | 0.1584 | 0.2277 | 9 | 16 | 23 | 0.089711 |
