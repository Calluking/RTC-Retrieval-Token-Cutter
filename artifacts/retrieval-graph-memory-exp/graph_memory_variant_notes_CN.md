# Graph Memory 变体说明

本文是 `graph_memory_variant_notes.md` 的中文版本。

该文件记录 graph memory 检索变体的实验备注，重点关注记忆/关系信号如何影响召回和排序。

阅读要点：

- graph memory 适合将历史上下文、文件关系和符号关系作为额外检索信号。
- 需要平衡记忆信号带来的召回提升和噪声扩散。
- 失败 case 应检查关系是否过旧、过宽或缺少目标相关边。
