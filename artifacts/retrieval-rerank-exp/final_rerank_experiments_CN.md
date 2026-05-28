# 最终 Rerank 实验

本文是 `final_rerank_experiments.md` 的中文版本。

该文件记录 rerank 阶段的最终实验结果，用于评估候选召回后重新排序的收益。

阅读要点：

- rerank 的目标是把已召回的正确候选推到更靠前位置。
- 关注 Top-1/Top-K 改善，以及 rerank 是否引入新的降级。
- 如果正确文件未进入候选集，rerank 无法弥补，需要回到召回路由调优。
