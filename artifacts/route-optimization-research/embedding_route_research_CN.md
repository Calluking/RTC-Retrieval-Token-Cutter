# Embedding 路由优化研究

本文是 `embedding_route_research.md` 的中文版本。

该研究记录 embedding 路由优化方向、实验观察和潜在改进。

阅读要点：

- 优化重点包括模型选择、chunk 粒度、向量维度、候选上限和语义噪声控制。
- embedding 适合语义相关但字面不同的 query。
- 需要通过 rerank 或融合策略控制误召回，并结合 BM25/symbol 提供精确信号。
