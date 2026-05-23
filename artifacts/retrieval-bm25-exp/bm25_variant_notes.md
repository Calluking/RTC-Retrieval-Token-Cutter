# BM25 Route Variants

This note summarizes BM25-style alternatives for the lexical route.

## Referenced Work

| Work | Why It Matters Here |
|---|---|
| Robertson and Zaragoza, *The Probabilistic Relevance Framework: BM25 and Beyond* | Core reference for BM25 and BM25F. BM25 combines term frequency, inverse document frequency, and document-length normalization. |
| Zaragoza et al., BM25F / fielded BM25 | Motivates treating structured documents as multiple weighted fields. For code, useful fields are `symbol`, `signature`, `path`, and `body`. |
| Lv and Zhai, *Lower-Bounding Term Frequency Normalization* | Motivates BM25+ and BM25L. These variants address over-penalizing very long documents that still contain query terms. |
| Language Modeling for Information Retrieval / Dirichlet smoothing | Alternative lexical retrieval family: rank by query likelihood under each document language model with collection smoothing. |
| BM25 parameter tuning literature | BM25's `k1` and `b` strongly affect retrieval. Code snippets are often short/structured, so default web-document settings may not be optimal. Trotman et al. discuss practical BM25/Lucene variants and parameter sensitivity. |

Useful links:

- BM25 and BM25F overview: https://doi.org/10.1561/1500000019
- BM25/BM25F Lucene implementation paper: https://arxiv.org/abs/0911.5046
- Lower-bounding TF normalization: https://timan.cs.illinois.edu/czhai/pub/cikm11-bm25.pdf
- Trotman et al., *Improvements to BM25 and Language Models Examined*: https://dl.acm.org/doi/10.1145/2063576.2063584

## Original BM25

Original BM25 scores a snippet by summing query-term contributions.

Process:

```text
query terms
  -> for each term:
       term frequency in snippet
       inverse document frequency in candidate corpus
       document length normalization
  -> sum term scores
```

The current offline baseline uses:

```text
k1 = 1.5
b = 0.75
document = path + symbol + signature + body
```

Weakness for code:

- Code snippets are structured, but default BM25 treats them as one flat document.
- Long classes/functions can be penalized heavily.
- Repeated body terms can dominate over a strong symbol or signature match.

## Tested Variants

| Variant | Idea |
|---|---|
| `bm25_default` | Current BM25 proxy: flat document, default-ish `k1=1.5`, `b=0.75`. |
| `bm25_tuned_short_code` | Lower `b` and `k1`: less length penalty and faster saturation. Intended for short/structured code snippets. |
| `bm25_plus` | Adds a lower bound to matching-term contribution so long matching snippets are not crushed. |
| `bm25_l` | Similar goal to BM25+, but shifts normalized term frequency for long documents. |
| `bm25f_code_fields` | Fielded BM25. Scores `symbol`, `signature`, `path`, and `body` separately with different weights. |
| `dirichlet_lm` | Query-likelihood language model with Dirichlet smoothing. Non-BM25 lexical baseline. |

## What `bm25_tuned_short_code` Changes

`bm25_tuned_short_code` is not a new retrieval family. It is still BM25, but
with parameters tuned for code snippets instead of normal web/news documents.

Default BM25 proxy:

```text
k1 = 1.5
b  = 0.75
```

Tuned short-code BM25:

```text
k1 = 0.9
b  = 0.35
```

Meaning:

| Parameter | Meaning | Default | Tuned |
|---|---|---:|---:|
| `k1` | Controls how much repeated term frequency helps. | 1.5 | 0.9 |
| `b` | Controls how strongly long documents/snippets are penalized. | 0.75 | 0.35 |

Effect:

```text
lower k1 -> repeated words saturate sooner
lower b  -> long snippets are penalized less
```

Why this fits code:

- Code chunks are already smaller than full documents.
- A longer class/function is not automatically less relevant.
- Repeated words in the body should not dominate over a good symbol/signature
  match.
- Exact matches in a slightly longer snippet should survive ranking.

This is supported by the BM25 literature because `k1` and `b` are tunable
parameters, not fixed constants. Robertson and Zaragoza describe BM25 as a
parameterized probabilistic ranking function. Trotman et al. examine BM25
variants and practical parameter behavior in search-engine settings. Our
experiment applies that same principle to code snippets: use lower length
normalization and stronger TF saturation because the documents are structured
code chunks.

## Experiment

Dataset:

```text
artifacts/legacy-search-dataset/search_targets.jsonl
```

Source candidates:

```text
artifacts/retrieval-eval/predictions.jsonl
```

Experiment output:

```text
artifacts/retrieval-bm25-exp/metrics.json
artifacts/retrieval-bm25-exp/route_accuracy.md
```

Scope:

```text
rerank_existing_4_route_top5_union
```

This means the experiment reranks the existing final candidate pool instead of
rebuilding the full candidate set from disk.

## Results

| Variant | Top1 | Top3 | Top5 |
|---|---:|---:|---:|
| `bm25_tuned_short_code` | 0.2673 | 0.4455 | 0.6139 |
| `bm25f_code_fields` | 0.2574 | 0.4950 | 0.5743 |
| `bm25_plus` | 0.2376 | 0.4257 | 0.5446 |
| `bm25_l` | 0.2376 | 0.4158 | 0.5347 |
| `dirichlet_lm` | 0.2673 | 0.4158 | 0.4851 |
| `bm25_default` | 0.2475 | 0.4059 | 0.4752 |

## Interpretation

BM25 is strong, but the default BM25 configuration is not best here.

Best Top5:

```text
bm25_tuned_short_code
```

This suggests the default length normalization is too aggressive for code
snippets. A lower `b` helps because code snippets are already chunked and do not
need web-document-style length correction.

Best Top3:

```text
bm25f_code_fields
```

This suggests the lexical route should understand code fields. A match in
`symbol` or `signature` should count more than one more occurrence in the body.

Practical recommendation:

```text
Use bm25_tuned_short_code as the first simple change.
Then test bm25f_code_fields in the real route, because it is more code-aware.
```
