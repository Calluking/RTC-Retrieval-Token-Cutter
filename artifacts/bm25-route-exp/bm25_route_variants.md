# BM25 Route Variants

Metric:

```text
grep candidate pool -> BM25-family route ranks snippets independently -> top1/top3/top5 hit
```

- usable_records: `101`
- candidate_limit: `80`
- max_snippets_per_record: `500`
- candidate_recall: `0.9307`

| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_score_time_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| bm25f_symbol_heavy | 0.3366 | 0.5050 | 0.6337 | 34 | 51 | 64 | 0.063072 |
| bm25f_code_fields_current | 0.3267 | 0.4653 | 0.5941 | 33 | 47 | 60 | 0.062539 |
| bm25f_identifier_summary | 0.2772 | 0.5149 | 0.5743 | 28 | 52 | 58 | 0.072696 |
| bm25f_path_heavy | 0.2673 | 0.4158 | 0.5545 | 27 | 42 | 56 | 0.063345 |
| bm25f_no_body | 0.3069 | 0.4455 | 0.5347 | 31 | 45 | 54 | 0.032882 |
| bm25_default | 0.2277 | 0.3663 | 0.4752 | 23 | 37 | 48 | 0.028064 |
| bm25_field_rrf | 0.1386 | 0.3069 | 0.4653 | 14 | 31 | 47 | 0.134963 |
