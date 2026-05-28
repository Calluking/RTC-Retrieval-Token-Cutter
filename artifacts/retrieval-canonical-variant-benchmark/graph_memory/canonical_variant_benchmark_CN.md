# Canonical Graph Memory Benchmark

本文是 `canonical_variant_benchmark.md` 的中文版本。

该 benchmark 聚焦 graph memory 路由在 canonical 数据集上的表现。

阅读要点：

- graph memory 适合利用文件、符号、引用或历史上下文关系进行补充召回。
- 重点观察它是否能在 BM25/embedding miss 时补上目标文件。
- 若噪声较大，需要检查图边构建、热度权重和融合策略。
