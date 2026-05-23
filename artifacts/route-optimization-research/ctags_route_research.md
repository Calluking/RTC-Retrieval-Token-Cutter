# Ctags / Symbol Route Research

This note covers step-2 route optimization for the symbol / ctags route.

Canonical metric:

```text
grep candidate pool -> ctags/symbol route ranks snippets independently -> top1/top3/top5 hit
```

## Research Basis

The main lesson from real code-search systems is that ctags is usually not a
standalone scoring formula. It provides a declaration index. Search systems then
rank symbol hits with exact/prefix matching, file/path scope, declaration kind,
and fallback lexical signals.

| source | relevant idea |
|---|---|
| Sourcegraph symbol search | Uses ctags to index repository symbols, matching declarations instead of plain text. It calls out exact matches, prefix matches, path filtering, and declaration categories. |
| Zoekt | Trigram-based code search; Universal Ctags is recommended because symbol information is a key ranking signal. |
| Universal Ctags | Provides the symbol/declaration extraction layer: names, kinds, paths, and locations. |
| Identifier splitting work | Code identifiers are compound words, so symbol search benefits from camelCase/snake_case splitting and abbreviation handling. |
| Reciprocal Rank Fusion | Useful baseline for combining separate symbol/signature/path/kind rankings. |

References:

- Sourcegraph symbol search: https://sourcegraph.com/docs/code-search/types/symbol
- Zoekt README: https://github.com/sourcegraph/zoekt
- Universal Ctags manual: https://docs.ctags.io/en/stable/man/ctags.1.html
- Sourcerer / structural code retrieval: https://doi.org/10.1016/j.scico.2012.04.008
- Lingua::IdSplitter paper: https://doi.org/10.1016/j.jss.2014.08.031
- Spiral identifier splitter: https://doi.org/10.21105/joss.00653
- Reciprocal Rank Fusion: https://doi.org/10.1145/1571941.1572114

## Variants Tested

Script:

```text
artifacts/ctags-route-exp/ctags_route_variants.py
```

Detailed output:

```text
artifacts/ctags-route-exp/ctags_route_variants.md
artifacts/ctags-route-exp/metrics.json
```

| variant | idea |
|---|---|
| `ctags_current_baseline` | Current weighted symbol/signature/path matching. |
| `exact_prefix_symbol` | Declaration-index style: exact symbol, prefix symbol, then substring/subtoken match. |
| `zoekt_like_symbol_signal` | Trigram/substr matching with symbol matches boosted as a code-search ranking signal. |
| `path_scoped_symbol` | Use the original grep path/scope as a soft boost over symbol matches. |
| `kind_aware_declaration` | Boost classes/functions/assignments when query intent implies a declaration kind. |
| `identifier_split_abbrev` | Split compound identifiers and match acronyms/abbreviations. |
| `field_rrf_symbol` | Rank symbol, signature, path, and kind fields separately, then fuse with RRF. |
| `hybrid_symbol_decl` | Conservative blend of the declaration-index signals. |

## Results

| variant | top1 | top3 | top5 | top1_count | top3_count | top5_count | avg_score_time_sec |
|---|---:|---:|---:|---:|---:|---:|---:|
| `ctags_current_baseline` | 0.3366 | 0.4950 | 0.6040 | 34 | 50 | 61 | 0.000559 |
| `path_scoped_symbol` | 0.4059 | 0.5149 | 0.5842 | 41 | 52 | 59 | 0.007219 |
| `hybrid_symbol_decl` | 0.2970 | 0.4158 | 0.5446 | 30 | 42 | 55 | 0.145469 |
| `exact_prefix_symbol` | 0.2475 | 0.3960 | 0.5248 | 25 | 40 | 53 | 0.005193 |
| `field_rrf_symbol` | 0.2277 | 0.3465 | 0.5149 | 23 | 35 | 52 | 0.013713 |
| `zoekt_like_symbol_signal` | 0.2772 | 0.4257 | 0.5050 | 28 | 43 | 51 | 0.014980 |
| `identifier_split_abbrev` | 0.2475 | 0.3861 | 0.4653 | 25 | 39 | 47 | 0.127872 |
| `kind_aware_declaration` | 0.2574 | 0.3762 | 0.4653 | 26 | 38 | 47 | 0.005226 |

## Interpretation

Best Top5 remains:

```text
ctags_current_baseline Top5 = 0.6040
```

Best Top1/Top3:

```text
path_scoped_symbol Top1 = 0.4059
path_scoped_symbol Top3 = 0.5149
```

So the current ctags route should stay as the route-top5 generator. However,
`path_scoped_symbol` is a useful reranking feature because it moves correct
results upward when the grep path/scope is meaningful.

Recommendation:

```text
Keep ctags_current_baseline for the symbol route candidate generator.
Consider adding path_scoped_symbol as a final reranking feature.
Do not replace ctags_current_baseline with the hybrid/fuzzy/identifier variants.
```

Current decision:

```text
Stick with ctags_current_baseline as the production ctags route.
```
