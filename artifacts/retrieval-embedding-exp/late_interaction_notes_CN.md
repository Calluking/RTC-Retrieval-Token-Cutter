# Late Interaction 说明

本文是 `late_interaction_notes.md` 的中文版本。

该文件记录 embedding late-interaction 检索思路、观察结果和调优方向。

阅读要点：

- late interaction 关注 query 与 chunk 内多个片段/维度的细粒度匹配。
- 它可能改善长 chunk 或语义分散 query 的排序。
- 需要平衡额外计算成本、payload 大小和实际召回收益。
