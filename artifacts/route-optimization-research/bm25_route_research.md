# BM25 / Keyword Frequency Route Research

This note covers step-2 route optimization for the keyword-frequency route.

Canonical metric:

```text
grep candidate pool -> BM25-family route ranks snippets independently -> top1/top3/top5 hit
```

## Current Setup

The current updated BM25 setup is:

```text
bm25f_code_fields_current
```

Under the canonical route metric:

```text
Top5 = 0.5941
```

So yes, `0.5941` is the expected Top5 for the current BM25F setup.

## Research Basis

| Method | Why It Matters |
|---|---|
| BM25 | Strong probabilistic lexical ranking baseline using term frequency, inverse document frequency, and length normalization. |
| BM25F | Fielded BM25. Code snippets naturally have fields: path, symbol, signature, body. |
| BM25+ / BM25L | Modify length normalization so long documents are not over-penalized. |
| Field weighting | Code identifiers in symbol/signature are often much denser than body text. |
| RRF over fields | Robustly combines rankings when different fields win different queries. |

References:

- Robertson and Zaragoza, *The Probabilistic Relevance Framework: BM25 and Beyond*: https://doi.org/10.1561/1500000019
- BM25F / Lucene fielded retrieval discussion: https://arxiv.org/abs/0911.5046
- Lv and Zhai, *Lower-Bounding Term Frequency Normalization*: https://timan.cs.illinois.edu/czhai/pub/cikm11-bm25.pdf
- Trotman et al., *Improvements to BM25 and Language Models Examined*: https://dl.acm.org/doi/10.1145/2063576.2063584
- Lucene BM25Similarity docs: https://lucene.apache.org/core/9_9_1/core/org/apache/lucene/search/similarities/BM25Similarity.html
- Zoekt, Sourcegraph's trigram code search engine: https://github.com/sourcegraph/zoekt

## Variants Tested

Script:

```text
artifacts/bm25-route-exp/bm25_route_variants.py
```

Results:

| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_score_time_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| `bm25f_symbol_heavy` | 0.3366 | 0.5050 | 0.6337 | 34 | 51 | 64 | 0.063072 |
| `bm25f_code_fields_current` | 0.3267 | 0.4653 | 0.5941 | 33 | 47 | 60 | 0.062539 |
| `bm25f_identifier_summary` | 0.2772 | 0.5149 | 0.5743 | 28 | 52 | 58 | 0.072696 |
| `bm25f_path_heavy` | 0.2673 | 0.4158 | 0.5545 | 27 | 42 | 56 | 0.063345 |
| `bm25f_no_body` | 0.3069 | 0.4455 | 0.5347 | 31 | 45 | 54 | 0.032882 |
| `bm25_default` | 0.2277 | 0.3663 | 0.4752 | 23 | 37 | 48 | 0.028064 |
| `bm25_field_rrf` | 0.1386 | 0.3069 | 0.4653 | 14 | 31 | 47 | 0.134963 |

## Interpretation

The best variant is:

```text
bm25f_symbol_heavy
```

It improves over the current BM25F setup:

```text
Top5: 0.5941 -> 0.6337
Top3: 0.4653 -> 0.5050
Top1: 0.3267 -> 0.3366
```

Why this makes sense:

- The dataset queries are often grep-like identifiers.
- Symbol and signature fields are more reliable than raw body frequency.
- Body text still helps, but too much body weight dilutes identifier matches.

The failed variants are also informative:

- `bm25f_path_heavy` underperforms, so path is useful but should not dominate.
- `bm25f_no_body` is faster but loses Top5, so body still contributes recall.
- `bm25_field_rrf` is bad here; per-field RRF loses the calibrated BM25F term
  frequency information.
- `bm25f_identifier_summary` has the best Top3 but lower Top5 than current,
  making it more useful as a reranker feature than as the route itself.

## Recommended BM25 Route

Use:

```text
bm25f_symbol_heavy
```

Field weights:

```text
symbol:    4.5, b=0.05
signature: 2.6, b=0.20
path:      1.2, b=0.20
body:      0.45, b=0.65
k1:        1.5
```

Production implication:

```text
BM25 route should be fielded and symbol/signature-heavy.
Do not use plain BM25 over concatenated path+symbol+signature+body.
```

## Non-BM25 Keyword Attempts

The user asked whether this improvement was only a BM25 weight change, and
whether a different lexical model could replace BM25 entirely. I tested five
non-BM25 variants with the same canonical route metric:

```text
grep candidate pool -> keyword route ranks snippets independently -> top1/top3/top5 hit
```

Script:

```text
artifacts/non-bm25-keyword-exp/non_bm25_keyword_variants.py
```

Detailed output:

```text
artifacts/non-bm25-keyword-exp/non_bm25_keyword_variants.md
```

| variant | method | top1 | top3 | top5 |
|---|---|---:|---:|---:|
| `bm25f_symbol_heavy_baseline` | current best BM25F baseline | 0.3366 | 0.5050 | 0.6337 |
| `dfr_pl2_fielded` | divergence-from-randomness / PL2 | 0.2673 | 0.3861 | 0.5446 |
| `lm_jelinek_mercer_fielded` | query likelihood LM, Jelinek-Mercer smoothing | 0.3366 | 0.4653 | 0.5248 |
| `lm_dirichlet_fielded` | query likelihood LM, Dirichlet smoothing | 0.2475 | 0.4356 | 0.5149 |
| `field_rrf_tfidf` | per-field TF-IDF ranks fused with RRF | 0.1782 | 0.3762 | 0.5050 |
| `tfidf_fielded` | fielded TF-IDF vector-space scoring | 0.3267 | 0.4059 | 0.4851 |

References:

- Salton and Buckley, *Term-weighting approaches in automatic text retrieval*: https://doi.org/10.1016/0306-4573(88)90021-0
- Ponte and Croft, *A Language Modeling Approach to Information Retrieval*: https://doi.org/10.1145/290941.291008
- Zhai and Lafferty, *A Study of Smoothing Methods for Language Models Applied to Ad Hoc Information Retrieval*: https://doi.org/10.1145/383952.384019
- Amati and van Rijsbergen, *Probabilistic Models of Information Retrieval Based on Measuring Divergence From Randomness*: https://doi.org/10.1145/582415.582416
- Cormack et al., *Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods*: https://doi.org/10.1145/1571941.1572114

Conclusion:

```text
The non-BM25 routes did not beat bm25f_symbol_heavy.
Best non-BM25 Top5: 0.5446
Best BM25F Top5:    0.6337
```

## Next Experiments

1. Tune around `bm25f_symbol_heavy`:

```text
symbol: 3.5, 4.5, 5.5
signature: 2.0, 2.6, 3.2
body: 0.3, 0.45, 0.6
```

2. Add exact symbol bonuses only as tie-breakers.

3. Test query-side identifier splitting with BM25F.

4. Try BM25F as final reranker feature together with graph RRF.

5. Compare latency after production implementation, because artifact scoring
   recomputes corpus stats per search.
