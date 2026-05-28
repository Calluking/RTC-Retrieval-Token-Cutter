# OpenClaw Legacy vs RTC，对齐后的运行器

日期：2026-05-21

本文比较重写 OpenClaw legacy 运行器后，前五个 Django SWE-Lite 任务的结果。legacy 运行器已从 RTC 运行器对齐而来，但禁用了 RTC 插件。这些运行跳过了 benchmark 验证（`SWE_SKIP_VALIDATION=1`），每个 agent 仍在任务本地 SWE 环境中执行了自己的复现和验证命令。

## 运行器对齐

- Legacy runner: `scripts/SWE/openclaw/legacy/run_swe_task_lite_plain_openclaw.sh`
- RTC runner: `scripts/SWE/openclaw/RTC/run_swe_task_lite_rtc_openclaw.sh`
- legacy runner 现在保留 RTC runner 的 SWE workspace 设置、本地 SWE-bench 环境设置、日志、session render、JSONL 捕获和工具摘要流程。
- legacy runner 禁用 `retrieval-token-cutter` OpenClaw 插件，并使用不带 RTC 工具要求的普通 SWE prompt。

## 成本和 Token 对比

| Task | Setup | Turns | Tool Calls | Tool Failures | Total Tokens | Input | Output | Cache Read | Cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| django__django-10914 | legacy | 36 | 43 | 2 | 1,388,940 | 41,868 | 10,752 | 1,336,320 | $0.01261378 |
| django__django-10914 | RTC | 35 | 43 | 1 | 2,067,603 | 64,062 | 11,093 | 1,992,448 | $0.01765357 |
| django__django-10924 | legacy | 47 | 46 | 0 | 1,665,844 | 35,626 | 14,474 | 1,615,744 | $0.01356444 |
| django__django-10924 | RTC | 27 | 29 | 0 | 1,477,325 | 49,679 | 13,886 | 1,413,760 | $0.01480167 |
| django__django-11001 | legacy | 31 | 30 | 2 | 946,890 | 32,107 | 7,519 | 907,264 | $0.00914064 |
| django__django-11001 | RTC | 14 | 15 | 0 | 584,697 | 42,694 | 7,347 | 534,656 | $0.00953136 |
| django__django-11019 | legacy | 42 | 41 | 1 | 2,153,366 | 48,588 | 27,082 | 2,077,696 | $0.02020283 |
| django__django-11019 | RTC | 51 | 51 | 0 | 3,677,760 | 61,766 | 40,570 | 3,575,424 | $0.03001803 |
| django__django-11039 | legacy | 32 | 31 | 0 | 928,652 | 28,387 | 7,593 | 892,672 | $0.00859970 |
| django__django-11039 | RTC | 17 | 15 | 1 | 620,427 | 38,393 | 5,266 | 576,768 | $0.00846445 |

## 差值，RTC 减 Legacy

| Task | Cost Delta | Token Delta | Turn Delta | Tool Call Delta |
|---|---:|---:|---:|---:|
| django__django-10914 | +$0.00503980 | +678,663 | -1 | 0 |
| django__django-10924 | +$0.00123722 | -188,519 | -20 | -17 |
| django__django-11001 | +$0.00039072 | -362,193 | -17 | -15 |
| django__django-11019 | +$0.00981520 | +1,524,394 | +9 | +10 |
| django__django-11039 | -$0.00013525 | -308,225 | -15 | -16 |

## 总计

| Setup | Total Cost | Total Tokens |
|---|---:|---:|
| legacy | $0.06412139 | 7,083,692 |
| RTC | $0.08046908 | 8,427,812 |
| RTC - legacy | +$0.01634769 | +1,344,120 |

## 说明

- 对齐后的 legacy prompt/tool schema 已经更接近 RTC：legacy tool schema 约 29.5k 字符，RTC 约 31.2k 字符。
- RTC 在 `10924`、`11001` 和 `11039` 上减少了轮次和工具调用，但 `10914`，尤其是 `11019`，仍消耗更多 cache-read 和总 token。
- 这说明剩余差距不再只是 legacy 工具 allow-list 不公平造成的；任务行为和 RTC search/edit 流程仍需要调优。
