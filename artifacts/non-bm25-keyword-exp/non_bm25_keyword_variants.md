# Non-BM25 Keyword Variants

Metric:

```text
grep candidate pool -> non-BM25 keyword route ranks snippets independently -> top1/top3/top5 hit
```

- usable_records: `101`
- candidate_limit: `80`
- max_snippets_per_record: `500`
- candidate_recall: `0.9307`

## Research Basis

These are still lexical / keyword-frequency routes, but they deliberately avoid
BM25 scoring. The goal was to check whether another classic IR family works
better for code snippets after grep has already narrowed the candidate pool.

| variant | method family | reference |
|---|---|---|
| `tfidf_fielded` | vector-space TF-IDF over code fields | Salton and Buckley, *Term-weighting approaches in automatic text retrieval*: https://doi.org/10.1016/0306-4573(88)90021-0 |
| `lm_dirichlet_fielded` | query-likelihood language model with Dirichlet smoothing | Zhai and Lafferty, *A Study of Smoothing Methods for Language Models Applied to Ad Hoc Information Retrieval*: https://doi.org/10.1145/383952.384019 |
| `lm_jelinek_mercer_fielded` | query-likelihood language model with Jelinek-Mercer smoothing | Ponte and Croft, *A Language Modeling Approach to Information Retrieval*: https://doi.org/10.1145/290941.291008 |
| `dfr_pl2_fielded` | divergence-from-randomness / PL2-style lexical scoring | Amati and van Rijsbergen, *Probabilistic Models of Information Retrieval Based on Measuring Divergence From Randomness*: https://doi.org/10.1145/582415.582416 |
| `field_rrf_tfidf` | rank fusion across path/symbol/signature/body TF-IDF field ranks | Cormack et al., *Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods*: https://doi.org/10.1145/1571941.1572114 |

`bm25f_symbol_heavy_baseline` is included only as the current best keyword-route
baseline. It is not one of the non-BM25 attempts.

## Results

| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_score_time_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| bm25f_symbol_heavy_baseline | 0.3366 | 0.5050 | 0.6337 | 34 | 51 | 64 | 0.064789 |
| dfr_pl2_fielded | 0.2673 | 0.3861 | 0.5446 | 27 | 39 | 55 | 0.144962 |
| lm_jelinek_mercer_fielded | 0.3366 | 0.4653 | 0.5248 | 34 | 47 | 53 | 0.154074 |
| lm_dirichlet_fielded | 0.2475 | 0.4356 | 0.5149 | 25 | 44 | 52 | 0.154456 |
| field_rrf_tfidf | 0.1782 | 0.3762 | 0.5050 | 18 | 38 | 51 | 0.145605 |
| tfidf_fielded | 0.3267 | 0.4059 | 0.4851 | 33 | 41 | 49 | 0.151770 |

## Interpretation

None of the non-BM25 variants beat the current best keyword route:

```text
bm25f_symbol_heavy Top5 = 0.6337
best non-BM25 Top5 = 0.5446  (dfr_pl2_fielded)
```

Useful observations:

- `dfr_pl2_fielded` is the best non-BM25 Top5, but it is still far below the
  BM25F baseline.
- `lm_jelinek_mercer_fielded` ties BM25F on Top1, but drops heavily at Top5.
- The language-model variants are slower in this artifact implementation because
  they compute per-search collection statistics over the grep candidate pool.
- Plain TF-IDF is not enough here; it misses the length-normalization behavior
  and field calibration that BM25F gives us.

Recommendation:

```text
Keep bm25f_symbol_heavy as the keyword-frequency route.
Do not replace the route with TF-IDF, query-likelihood LM, DFR/PL2, or field RRF.
```
