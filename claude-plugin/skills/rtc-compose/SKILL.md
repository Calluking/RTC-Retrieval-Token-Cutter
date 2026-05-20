---
name: rtc-compose
description: Use the terminal command rtc-compose to retrieve composed Retrieval Token Cutter context.
---

# Retrieval Token Cutter Compose

Use the terminal command:

```bash
claude-plugin/bin/rtc-compose "<query>"
```

Use this when the user asks to recall previous decisions, search memory, or asks `/rtc-compose`.
Summarize the returned sections clearly. If nothing is found, suggest a narrower query.
