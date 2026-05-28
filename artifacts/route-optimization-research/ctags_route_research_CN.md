# Ctags 路由优化研究

本文是 `ctags_route_research.md` 的中文版本。

该研究记录 ctags/symbol 路由优化方向。

阅读要点：

- 优化重点包括 symbol 抽取覆盖、语言支持、符号归一化和 query 对齐。
- 对符号型 query，ctags 可显著减少搜索空间。
- 需要与 BM25/embedding/graph 结合，避免只依赖符号导致漏召回。
