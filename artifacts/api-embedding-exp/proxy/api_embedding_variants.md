# Fixed API Embedding Variants

- model: `text-embedding-3-large`
- backend: `proxy`
- dimensions: `512`
- usable_records: `101`
- candidate_limit: `80`
- max_snippets_per_record: `200`
- candidate_recall: `0.9307`
- avg_embedding_api_and_cache_sec: `0.079625`

## Default Mapping

| variant | relationship to current production |
|---|---|
| `api_l2_raw_query` | True current production shape: raw query embedding vs current L2 `content.md` text with code-location header. Not yet implemented here as a named variant. |
| `api_structured_raw_query` | Closest implemented variant to current default; raw query plus structured snippet document. |
| `api_structured_identifier_query` | New query-formatting experiment. |
| `api_identifier_summary` | New document-formatting experiment. |
| `api_scope_query` | New query-formatting experiment using grep path/scope. |
| `api_field_rrf` | New multi-field/multi-vector ranking experiment. |

| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count |
|---|---:|---:|---:|---:|---:|---:|
| api_scope_query | 0.3564 | 0.4752 | 0.5545 | 36 | 48 | 56 |
| api_structured_raw_query | 0.2475 | 0.3762 | 0.5050 | 25 | 38 | 51 |
| api_structured_identifier_query | 0.2277 | 0.3564 | 0.4752 | 23 | 36 | 48 |
| api_identifier_summary | 0.3267 | 0.4554 | 0.4554 | 33 | 46 | 46 |
| api_field_rrf | 0.3267 | 0.4158 | 0.4554 | 33 | 42 | 46 |
