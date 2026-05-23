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
- avg_candidate_build_sec: 1.123915
- avg_memory_graph_build_sec: 0.000000

## bm25

| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_score_time_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| bm25f_code_fields | 0.3267 | 0.4653 | 0.5941 | 33 | 47 | 60 | 0.168785 |
| bm25_l | 0.2376 | 0.3861 | 0.4950 | 24 | 39 | 50 | 0.081901 |
| dirichlet_lm | 0.3168 | 0.4059 | 0.4752 | 32 | 41 | 48 | 0.068681 |
| bm25_tuned_short_code | 0.2970 | 0.4059 | 0.4752 | 30 | 41 | 48 | 0.066525 |
| bm25_default | 0.2277 | 0.3663 | 0.4752 | 23 | 37 | 48 | 0.065493 |
| bm25_plus | 0.2475 | 0.3762 | 0.4653 | 25 | 38 | 47 | 0.066719 |
