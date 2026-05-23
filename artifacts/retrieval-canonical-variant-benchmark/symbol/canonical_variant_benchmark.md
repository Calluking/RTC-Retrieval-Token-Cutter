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
- avg_candidate_build_sec: 0.799635
- avg_memory_graph_build_sec: 0.000000

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
