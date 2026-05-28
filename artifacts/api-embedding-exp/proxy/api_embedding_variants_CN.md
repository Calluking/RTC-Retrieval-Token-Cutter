# API Embedding 变体实验

本文是 `api_embedding_variants.md` 的中文版本。

该实验记录通过 OpenAI-compatible API embedding 后端进行检索路由/召回变体测试的结果。请结合英文原表中的 query、variant、score、命中情况和备注查看具体数值。

阅读要点：

- 关注不同 embedding API 配置对召回质量的影响。
- 对比命中路径、排名和失败样例，判断是否需要调整 embedding provider、模型或候选过滤策略。
- 若英文表中出现 miss 或 low-rank hit，应优先检查 query 表达、chunk 粒度和 fallback 检索路径。
