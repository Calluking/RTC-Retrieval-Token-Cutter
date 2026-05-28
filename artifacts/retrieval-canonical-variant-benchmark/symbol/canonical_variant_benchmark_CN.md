# Canonical Symbol Benchmark

本文是 `canonical_variant_benchmark.md` 的中文版本。

该 benchmark 聚焦 symbol/ctags 路由在 canonical 数据集上的表现。

阅读要点：

- symbol 路由对明确类名、函数名、方法名的 query 更有优势。
- 失败通常来自 symbol 未索引、语言解析不足或 query 未对齐真实 symbol。
- 与文本和语义路由融合后，symbol 可提升精确定位能力。
