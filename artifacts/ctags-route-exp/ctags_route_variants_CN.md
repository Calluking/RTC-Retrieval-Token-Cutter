# Ctags 路由变体实验

本文是 `ctags_route_variants.md` 的中文版本。

该实验记录基于 ctags/symbol 的路由变体表现，用于评估符号级检索对代码定位的帮助。

阅读要点：

- ctags 路由适合函数名、类名、方法名、常量名等符号型 query。
- 关注目标 symbol 是否被正确索引，以及 symbol hit 是否能把目标文件推到靠前位置。
- 如果结果不稳定，应检查语言支持、ctags 生成质量、符号归一化和与 BM25/embedding 的融合方式。
