# Embedding 路由准确率

本文是 `route_accuracy.md` 的中文版本。

该报告记录 embedding 路由实验的准确率。英文原表包含完整 case 和指标。

阅读要点：

- 关注语义 query 是否能召回目标实现文件。
- 对 miss case 检查 chunk 语义、模型选择、向量维度和候选数量。
- 该结果可用于决定 embedding 在融合检索中的权重。
