# 检索 Miss 样例

本文是 `misses.md` 的中文版本。

该文件汇总检索评估中的 miss 样例，用于分析目标文件未被召回或排名过低的原因。

阅读要点：

- 将 miss 按 query 表达、索引内容、chunk 粒度、路由缺失和融合排序问题分类。
- 优先处理能代表一类问题的高频 miss。
- 修复后应回到对应 route accuracy 或 benchmark 文件验证改善。
