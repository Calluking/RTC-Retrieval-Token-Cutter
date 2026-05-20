---
name: rtc-add-history
description: Use the terminal command rtc-add-history to import Claude Code transcript history into Retrieval Token Cutter.
---

# Retrieval Token Cutter Add History

Use the terminal command:

```bash
claude-plugin/bin/rtc-add-history --dry-run
```

Show the user the dry-run totals first. Only run the import after explicit confirmation:

```bash
claude-plugin/bin/rtc-add-history --yes
```

Use this when the user asks to add/import project history or asks `/rtc-add-history`.
