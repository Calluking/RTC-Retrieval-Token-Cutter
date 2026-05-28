# OpenClaw RTC vs Legacy Token 构成

本报告比较前五个 Django SWE-bench Lite OpenClaw 运行。RTC 使用当前设置重新运行；legacy 使用每个任务最新可用的匹配完成运行。benchmark 验证被跳过，但 agent 侧验证仍然执行。

## 运行

| task | legacy run | rtc run |
|---|---|---|
| `django__django-10914` | `20260521-073017-swe-lite-openclaw-plain-r225-p174964` | `20260521-223946-swe-lite-openclaw-rtc-r601-p15220` |
| `django__django-10924` | `20260521-073528-swe-lite-openclaw-plain-r226-p176344` | `20260521-224750-swe-lite-openclaw-rtc-r602-p17974` |
| `django__django-11001` | `20260521-222250-swe-lite-openclaw-plain-r56-p10706` | `20260521-221245-swe-lite-openclaw-rtc-r56-p7424` |
| `django__django-11019` | `20260521-101713-swe-lite-openclaw-plain-r21019-p46354` | `20260521-225547-swe-lite-openclaw-rtc-r603-p20743` |
| `django__django-11039` | `20260521-133915-swe-lite-openclaw-plain-r22039-p78163` | `20260521-230857-swe-lite-openclaw-rtc-r604-p25878` |

## 成本和 Token 摘要

| setup | cost | turns | tool calls | failures | input | output | cache read | total tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| legacy | $0.05647 | 151 | 159 | 7 | 160,880 | 74,084 | 4,716,672 | 4,951,636 |
| rtc | $0.08047 | 144 | 153 | 2 | 256,594 | 78,162 | 8,093,056 | 8,427,812 |

RTC 成本差值：`$0.02400`，比 legacy 高 42.5%。

RTC token 差值：`3,476,176` 总 token，比 legacy 高 70.2%。

## 成本构成

| setup | input cost | output cost | cache-read cost | total cost | input % | output % | cache-read % |
|---|---:|---:|---:|---:|---:|---:|---:|
| legacy | $0.02252 | $0.02074 | $0.01321 | $0.05647 | 39.9% | 36.7% | 23.4% |
| rtc | $0.03592 | $0.02189 | $0.02266 | $0.08047 | 44.6% | 27.2% | 28.2% |

观察：输出成本不是全部原因。RTC 减少了一些工具循环，但额外工具 schema、RTC policy 文本、search/read/edit payload，以及更长上下文增长，都会抬高 input 和 cache-read 成本。

## 单任务对比

| task | legacy cost | rtc cost | delta | legacy turns/tools/fail | rtc turns/tools/fail | legacy tokens | rtc tokens | note |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `django__django-10914` | $0.00962 | $0.01765 | $0.00804 | 31/34/0 | 35/43/1 | 969,039 | 2,067,603 | legacy cheaper |
| `django__django-10924` | $0.01123 | $0.01480 | $0.00357 | 30/34/2 | 27/29/0 | 980,693 | 1,477,325 | legacy cheaper |
| `django__django-11001` | $0.00862 | $0.00953 | $0.00091 | 29/28/4 | 14/15/0 | 794,876 | 584,697 | legacy cheaper |
| `django__django-11019` | $0.01762 | $0.03002 | $0.01240 | 26/26/0 | 51/51/0 | 1,219,949 | 3,677,760 | legacy cheaper |
| `django__django-11039` | $0.00939 | $0.00846 | $-0.00092 | 35/37/1 | 17/15/1 | 987,079 | 620,427 | RTC cheaper |

## 工具构成

| task | legacy tools | rtc tools |
|---|---|---|
| `django__django-10914` | `edit` 1, `exec` 23, `read` 10 | `exec` 23, `read` 1, `rtc_edit_file` 5, `rtc_read` 5, `rtc_search_code` 9 |
| `django__django-10924` | `edit` 1, `exec` 24, `read` 8, `write` 1 | `exec` 18, `rtc_edit_file` 1, `rtc_read` 1, `rtc_search_code` 9 |
| `django__django-11001` | `edit` 6, `exec` 16, `read` 6 | `exec` 7, `rtc_edit_file` 2, `rtc_read` 2, `rtc_search_code` 4 |
| `django__django-11019` | `edit` 5, `exec` 14, `read` 7 | `exec` 40, `rtc_edit_file` 4, `rtc_read` 3, `rtc_search_code` 4 |
| `django__django-11039` | `edit` 1, `exec` 25, `read` 7, `write` 4 | `exec` 11, `rtc_edit_file` 1, `rtc_search_code` 3 |

显著问题：

- `django__django-10914` 的 RTC 运行仍记录了一次 native `read`，与 guard-mode 意图不一致。
- `django__django-11019` 的 RTC 运行执行了 `40` 次 `exec`，主导了该运行成本。这不只是 search/edit payload 问题，agent 持续通过 shell 命令验证和探索。
- RTC 总体失败更少（`2` vs `7`），行为更干净，但更干净还不等于更便宜。

## Prompt 构成

原报告保留了每个任务的 system chars、project context、skills、tool schemas、current/final prompt、AGENTS、SOUL 等字段。核心结论是：RTC 比 legacy 多约 8k 字符固定 tool-schema 开销，并额外注入 RTC policy 与上下文覆盖文本。

## Prompt 是否相同？

不相同。benchmark issue 文本和本地 SWE 环境说明大体相同，但 RTC 额外前置 Retrieval Token Cutter policy block，并改变 workspace guidance。OpenClaw 也看到不同的工具 schema 集合。

主要差异：

- RTC 增加 `[Retrieval Token Cutter]` 任务块。
- RTC 要求编辑前使用 `rtc_search_code`。
- RTC 禁止对 source/code 改动使用 OpenClaw 内置 `edit`、`write` 和 `file_write`。
- RTC 指示模型使用 `rtc_edit_file`，并从 `rtc_search_code.content_excerpt` 构造 `old_string`。
- RTC 增加对 `AGENTS.md`、`SOUL.md`、`TOOLS.md` 和默认 OpenClaw 习惯的上下文覆盖。
- RTC 说明不要对仓库 source/docs 使用 native `read`，fallback 应使用 `rtc_read`。
- RTC 增加效率策略和 search-limit 策略。
- RTC 的 `SOUL.md` 更短且针对 RTC；legacy 的 SOUL 更长、更通用。
- RTC 工具 schema 更大，因为多了 `rtc_read`、`rtc_health`、`rtc_index_codebase`、`rtc_search_code` 和 `rtc_edit_file`。

## 为什么 RTC 仍更贵

五次运行聚合显示，RTC 轮次和工具数略少，但 input/cache-read 总量显著更大：

- Input tokens：legacy `160,880` vs RTC `256,594`。
- Cache-read tokens：legacy `4,716,672` vs RTC `8,093,056`。
- Output tokens：legacy `74,084` vs RTC `78,162`。

这说明 RTC 的成本主要来自反复携带的大上下文，而不仅是最终回答。固定开销来自更多 tool-schema 字符和 policy 注入；动态开销来自 `rtc_search_code` / `rtc_read` 输出以及重复验证循环，尤其是 `11019`。

## 建议的下一步削减

1. 将 RTC prompt injection 缩短 50-70%，只保留硬性要求，移除重复表述。
2. SWE 运行中从 OpenClaw 注册里隐藏未使用的 RTC 工具，可能包括 `rtc_health` 和 `rtc_index_codebase`。
3. 进一步减少 `rtc_search_code` 输出，默认只返回 `hit_count`、`file`、`start_line`、`end_line`、`content_excerpt`，不返回 candidate/debug 字段。
4. 调查 `10914` 为什么在 guard mode 下仍允许 native `read`。
5. 给 OpenClaw RTC 添加验证预算指令，因为 `11019` 执行了 `40` 次 `exec`。
6. 如果可行，禁用 SWE 运行中的通用 OpenClaw skills/tools；legacy 和 RTC 都携带很多无关 schema，但 RTC 在此基础上还多付额外成本。
