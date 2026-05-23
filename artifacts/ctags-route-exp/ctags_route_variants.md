# Ctags / Symbol Route Variants

Metric:

```text
grep candidate pool -> ctags/symbol route ranks snippets independently -> top1/top3/top5 hit
```

- usable_records: `101`
- candidate_limit: `80`
- max_snippets_per_record: `500`
- candidate_recall: `0.9307`
- avg_snippets_per_search: `493.24`

## Research Basis

| variant | idea | reference |
|---|---|---|
| `exact_prefix_symbol` | Treat ctags output as a declaration index; rank exact and prefix declaration-name matches first. | Sourcegraph symbol search uses ctags to index declarations; Sourcegraph docs also mention exact and prefix symbol-search behavior. |
| `zoekt_like_symbol_signal` | Use substring/trigram-like code-search matching, with symbol matches as a key ranking signal. | Zoekt is a trigram-based code search engine and recommends Universal Ctags because symbol information is a key ranking signal. |
| `path_scoped_symbol` | Combine symbol matches with original grep path/scope, similar to file-qualified code-search queries. | Zoekt/Sourcegraph support file/path query qualifiers; Sourcegraph symbol behavior references path-prefix filtering for symbol sidebar use cases. |
| `kind_aware_declaration` | Use ctags declaration categories: class/type/function/assignment. | Sourcegraph docs describe ctags symbols being categorized by declaration type in the symbol sidebar. |
| `identifier_split_abbrev` | Split identifiers and support acronym/abbreviation matches. | Identifier splitting work such as Lingua::IdSplitter and Spiral targets compound code identifiers. |
| `field_rrf_symbol` | Fuse independent symbol/signature/path/kind ranks. | Reciprocal Rank Fusion is a robust rank-combination baseline. |
| `hybrid_symbol_decl` | Conservative blend of declaration-index signals. | Practical code-search engines combine multiple ranking signals rather than relying on one raw symbol score. |

References:

- Sourcegraph symbol search: https://sourcegraph.com/docs/code-search/types/symbol
- Zoekt README: https://github.com/sourcegraph/zoekt
- Universal Ctags manual: https://docs.ctags.io/en/stable/man/ctags.1.html
- Sourcerer / structural code retrieval: https://doi.org/10.1016/j.scico.2012.04.008
- Lingua::IdSplitter paper: https://doi.org/10.1016/j.jss.2014.08.031
- Spiral identifier splitter: https://doi.org/10.21105/joss.00653
- Reciprocal Rank Fusion: https://doi.org/10.1145/1571941.1572114

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
