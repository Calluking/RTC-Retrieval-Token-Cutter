---
name: rtc-add-history
description: 使用终端命令 rtc-add-history 将 Claude Code transcript 历史导入 Retrieval Token Cutter。
---

# Retrieval Token Cutter 添加历史

使用终端命令：

```bash
claude-plugin/bin/rtc-add-history --dry-run
```

先向用户展示 dry-run 汇总结果。只有在用户明确确认后，才执行真正导入：

```bash
claude-plugin/bin/rtc-add-history --yes
```

当用户要求添加/导入项目历史，或请求 `/rtc-add-history` 时使用本技能。
