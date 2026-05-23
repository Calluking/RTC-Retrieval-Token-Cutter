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
- avg_candidate_build_sec: 1.118180
- avg_memory_graph_build_sec: 0.044609

## graph_memory

| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_score_time_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| l1_relation_rrf | 0.3366 | 0.5050 | 0.6337 | 34 | 51 | 64 | 0.053729 |
| l1_relation_2hop_decay | 0.3366 | 0.4950 | 0.6139 | 34 | 50 | 62 | 0.015623 |
| l1_query_gated_walk | 0.3366 | 0.4950 | 0.6139 | 34 | 50 | 62 | 0.125906 |
| l1_relation_1hop | 0.3366 | 0.4950 | 0.5743 | 34 | 50 | 58 | 0.007321 |
| l1_relation_pagerank | 0.2079 | 0.3762 | 0.5644 | 21 | 38 | 57 | 0.042933 |
