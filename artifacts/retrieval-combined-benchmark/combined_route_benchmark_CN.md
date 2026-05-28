# 组合路由 Benchmark

本文是 `combined_route_benchmark.md` 的中文版本。

该 benchmark 比较组合检索路由的整体效果，通常包含 BM25、embedding、ctags/symbol、graph 等信号融合。

阅读要点：

- 关注组合后是否提升 Top-K 召回和目标文件排名。
- 分析失败 case 时，应判断是单一路由未召回，还是融合排序压低了正确结果。
- 该结果可指导后续融合权重、候选上限和 fallback 策略。
