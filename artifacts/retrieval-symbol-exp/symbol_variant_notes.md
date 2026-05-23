# Symbol Matching Variants

This note summarizes ctags/symbol-style retrieval variants.

For the consolidated routing table across embedding, BM25, and symbol trials,
see:

```text
artifacts/retrieval-routing-trials.md
```

## Referenced Work

| Work | Why It Matters Here |
|---|---|
| Ctags / Universal Ctags | Symbol search starts from extracted declarations: classes, functions, variables, methods, etc. |
| Sourcegraph symbol search / Zoekt | Practical code search systems use ctags symbols as an important ranking and navigation signal. |
| Sourcerer / CodeRank | Shows that structural code information can improve source-code retrieval beyond text alone. |
| Identifier splitting work, including Lingua::IdSplitter and Spiral | Symbol search depends heavily on splitting `FileStoragePermissions` into natural terms like `file`, `storage`, `permissions`. |
| Fuzzy matching / edit-distance style matching | Useful for misspellings, partial names, abbreviations, and query-symbol mismatch. |

Useful links:

- Sourcegraph symbol search: https://sourcegraph.com/docs/code-search/types/symbol
- Zoekt notes that Universal Ctags is a key signal in ranking: https://github.com/sourcegraph/zoekt
- Sourcerer: https://link.springer.com/article/10.1007/s10618-008-0118-x
- Spiral identifier splitting: https://joss.theoj.org/papers/10.21105/joss.00653
- From source code identifiers to natural language terms: https://www.sciencedirect.com/science/article/abs/pii/S0164121214002179

## Original Symbol Route

The current offline ctags proxy is a weighted symbol matcher.

Process:

```text
query terms
  -> match against symbol
  -> match against signature
  -> match against path
  -> add weighted scores
```

Rough behavior:

```text
exact symbol match      -> high score
substring symbol match  -> medium score
signature match         -> medium score
path match              -> low score
```

This is strong because many SWE searches are already symbol-like:

```text
FileStoragePermissions
upload_to
get_storage_class
test_nested_blueprint
```

## Tested Variants

| Variant | Idea |
|---|---|
| `ctags_default` | Current weighted symbol/signature/path matching. |
| `identifier_subtoken` | Split camelCase/snake_case identifiers and match query terms against pieces. |
| `fuzzy_symbol` | Use fuzzy sequence similarity for partial/typo-like symbol matches. |
| `acronym_abbrev` | Match abbreviations/acronyms, e.g. `FSP` to `FileStoragePermissions`. |
| `kind_aware_symbol` | Boost symbol hits whose kind matches query intent, such as class/function/setting. |
| `symbol_graph_neighbor` | Find symbol anchors, then expand to nearby same-file symbols. |
| `ctags_plus_subtoken` | Hybrid: mostly current ctags, plus identifier subtokens. |
| `ctags_plus_fuzzy` | Hybrid: mostly current ctags, plus fuzzy symbol matching. |
| `all_symbol_features` | Hybrid of ctags, subtoken, fuzzy, acronym, and kind-aware features. |

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
artifacts/retrieval-symbol-exp/metrics.json
artifacts/retrieval-symbol-exp/route_accuracy.md
```

Scope:

```text
rerank_existing_4_route_top5_union
```

## Results

| Variant | Top1 | Top3 | Top5 |
|---|---:|---:|---:|
| `ctags_default` | 0.3366 | 0.4851 | 0.5743 |
| `ctags_plus_fuzzy` | 0.3069 | 0.4950 | 0.5644 |
| `ctags_plus_subtoken` | 0.2871 | 0.4554 | 0.5644 |
| `fuzzy_symbol` | 0.2475 | 0.4653 | 0.5545 |
| `all_symbol_features` | 0.2574 | 0.3960 | 0.5545 |
| `acronym_abbrev` | 0.2376 | 0.3861 | 0.4950 |
| `identifier_subtoken` | 0.2574 | 0.3762 | 0.4851 |
| `symbol_graph_neighbor` | 0.2574 | 0.3663 | 0.4653 |
| `kind_aware_symbol` | 0.2574 | 0.3069 | 0.4653 |

## Interpretation

The current ctags-style symbol matcher is already the best overall on this
dataset.

Best Top1 and Top5:

```text
ctags_default
```

Best Top3:

```text
ctags_plus_fuzzy
```

This suggests fuzzy matching can occasionally help retrieve a target into the
top three, but it also introduces enough noise to hurt Top1 and Top5.

Practical recommendation:

```text
Keep the current ctags_default as the symbol route.
Consider ctags_plus_fuzzy only as a small auxiliary feature in final fusion,
not as a replacement for the current symbol score.
```
