# Symbol 路由准确率

本文是 `route_accuracy.md` 的中文版本。

该报告记录 symbol/ctags 路由准确率。英文原表包含完整 case 和排名数据。

阅读要点：

- symbol 路由适合明确符号名、API 名、类名或方法名 query。
- 失败时检查 symbol 是否被索引、语言解析是否支持，以及 query 是否与真实符号一致。
- 该结果可帮助决定 symbol 信号在融合检索中的权重。
