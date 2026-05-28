---
name: rtc-compose
description: 使用终端命令 rtc-compose 检索组合后的 Retrieval Token Cutter 上下文。
---

# Retrieval Token Cutter Compose

使用终端命令：

```bash
claude-plugin/bin/rtc-compose "<query>"
```

当用户要求回忆之前的决策、搜索记忆，或请求 `/rtc-compose` 时使用本技能。

清晰总结返回的各个 section。如果没有找到内容，建议用户使用更窄的查询。
