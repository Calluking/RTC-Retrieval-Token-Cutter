# Canonical Embedding Benchmark

本文是 `canonical_variant_benchmark.md` 的中文版本。

该 benchmark 聚焦 canonical 数据集上的 embedding 检索表现。

阅读要点：

- embedding 更适合语义相近但字面不同的 query。
- 观察 miss case 时，应检查 chunk 内容是否包含足够语义上下文。
- 与 BM25/ctags 结合时，可用该结果判断 embedding 权重是否合理。
