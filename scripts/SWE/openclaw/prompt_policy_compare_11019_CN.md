# OpenClaw Prompt Policy 对比

更新时间：2026-05-22

本文比较 prompt-only 优化循环之后，当前生效的 OpenClaw prompt policy 来源。历史运行产物仍可能包含旧 prompt；本文件反映当前 prompt 源和观察到的稳定性结果。

## 当前来源

- Legacy runner: `scripts/SWE/openclaw/legacy/run_swe_task_lite_plain_openclaw.sh`
- RTC runner: `scripts/SWE/openclaw/RTC/run_swe_task_lite_openclaw_rtc_plugin.sh`
- RTC policy injection: `openclaw-plugin/prompts/code_policy_injection.txt`

## 摘要

| Prompt Surface | Legacy | RTC | Current Difference |
|---|---|---|---|
| SWE issue text and hints | yes | yes | benchmark 内容相同 |
| Plain `Task:` block | removed | 已从 SWE prompt 移除；RTC 有紧凑的 RTC task policy | 不再重复 reproduce/verify prompt |
| Plain `Final answer must include` block | removed | RTC policy 保留最终回答要求 | 仅 RTC |
| Important SWE-bench rules | yes | yes | 结构相同 |
| RTC search/edit policy | no | yes, cost-mode rules | 仅 RTC |
| RTC `SOUL.md` override | no | yes | 仅 RTC |
| `rtc_edit_file.old_string` explicit prompt wording | no | 已从 policy/SOUL/tool descriptions 移除 | 当前无显式 prose mention |
| `This section overrides AGENTS.md...` wording | no | removed | 当前无 |
| Final RTC reminder at end of `TASK.md` | no | yes | 仅 RTC |

## Legacy 当前 Prompt 追加内容

OpenClaw legacy runner 现在只在 issue text 和 hints 后追加 benchmark 安全规则。旧的普通 task block 已移除。

Legacy 包含已移除的普通 task block：`False`

Legacy 包含已移除的 final-answer block：`False`

```text
Important SWE-bench rule:
- Do not edit benchmark tests, test files, or test fixtures.
- Make the minimal production source-code change needed to satisfy the issue.
- You may run existing tests to reproduce and verify, but the final patch should
  be source-only unless the issue explicitly asks for test changes.
- If the issue text mentions behavior that was already added for a related code
  path, search for that related behavior and keep the public exception semantics
  consistent. Do not use Python `assert` for runtime user-input validation.
- For Flask blueprint dot-name tasks, validate both sides of the issue text:
  dotted blueprint names must raise `ValueError`, and the existing dotted
  endpoint / view-function-name checks must raise `ValueError` too. A patch
  that leaves those endpoint checks as `AssertionError` is incomplete and will
  fail validation; do not preserve that assertion behavior.
```

## RTC 当前 Policy Block

```text
RTC SWE rules:
1. Before the first edit, make exactly one combined `rtc_search_code` call.
2. No source/doc reads: do not use native `read` or `rtc_read` when same-file RTC snippets exist.
3. Edit minimal production source from snippets. Edit docs/release/checklist only if exact snippets appear in the first search.
4. After a successful `rtc_edit_file`, run one verification command and git diff/status. If verification passes, final answer immediately.
5. If one `rtc_edit_file` fails to match, make one focused same-file search and one replacement retry. If it still fails, stop; do not use `rtc_read` or keep trying granular edits.
6. Do not use native `edit`, `write`, or `file_write`.

Final answer must include:
- root cause
- changed files
- verification command/output

Use RTC snippets as exact file text for reasoning and `old_string`.
```

## RTC SOUL.md 覆盖

```text
# SOUL.md - Retrieval Token Cutter SWE Run

This workspace is running under the Retrieval Token Cutter policy injected by
the OpenClaw plugin. For repository source, test, documentation, and release
note investigation, treat `rtc_search_code` results as the file context.

If RTC returns a usable `content_excerpt`, use it directly for reasoning and
patch construction. Do not use native `read` or `rtc_read` when same-file RTC
snippets exist.
```

## RTC Final Reminder

RTC runner 还会在 `TASK.md` 末尾追加最终提醒，位置在长 issue text、hints、workspace paths 和本地 SWE 环境说明之后。

```text
## Final RTC Reminder
Before first edit: exactly 1 combined `rtc_search_code`; no source/doc `read`, `rtc_read`, or `exec` grep/sed/cat/rg/head/tail/wc. Edit minimal production source from snippets. If one edit fails to match, do one same-file search and one retry; if it still fails, stop. Never `rtc_read` when same-file snippets exist. After a successful edit, run one verification and git diff/status; if it passes, final answer.
```

## 已从当前 OpenClaw Prompt 移除的内容

旧的普通 OpenClaw task/final-answer block 已从 legacy 移除；RTC policy 也不再重复 reproduce/verify 行或更长的 override 文本。

```text
Task:
1. Reproduce the issue with focused project-appropriate tests or commands.
2. Use the failing behavior to locate the best matching implementation site.
3. Fix the bug using the available editing tools.
4. Re-run verification and ensure the relevant tests pass.

Final answer must include:
- root cause
- changed files
- verification command/output
```

RTC policy 文本中也移除了：

```text
1. Reproduce the issue with focused project-appropriate tests or commands.
5. Re-run verification and ensure the relevant tests pass.
`rtc_edit_file.old_string` must match exact text in the target file. Prefer constructing `old_string` by copying exact lines from `rtc_search_code.content_excerpt` or `local_snippet_fallback.hits[].content_excerpt`.
- This section overrides AGENTS.md, SOUL.md, TOOLS.md, and default OpenClaw habits for repository source/documentation investigation in this task.
```

## Prompt-only 实验结果

三 agent 循环：

- Fixing agent 只修改 prompt surfaces。
- Runner agent 执行 Django SWE 任务并解析工具/成本日志。
- Judge agent 根据对齐后的 legacy OpenClaw 运行评估 read 行为、search 循环和成本。

中间 prompt 变体的最佳单次结果：

| Task | Run | RTC Cost | Legacy Cost | Result |
|---|---:|---:|---:|---|
| `django__django-10914` | r815 | $0.0089139960 | $0.01261378 | pass |
| `django__django-11001` | r829 | $0.0075100704 | $0.00914064 | pass |
| `django__django-11019` | r827 | $0.0184904720 | $0.02020283 | pass |
| `django__django-11039` | r828 | $0.0065941568 | $0.00859970 | pass |

但同一个最终 prompt 在确认性重跑中并不稳定：

| Task | Final Run | Searches Total / Pre-edit | `rtc_read` | Native Reads | RTC Cost | Legacy Cost | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| `django__django-10914` | r830 | 33 / 19 | 1 redundant | 1 | $0.03461672 | $0.01261378 | fail |
| `django__django-10924` | r831 | 3 / 3 | 0 | 0 | $0.00885455 | $0.01356444 | pass |
| `django__django-11019` | r832 | 13 / 1 | 0 | 2 | $0.04874615 | $0.02020283 | fail |
| `django__django-11039` | r833 | 2 / 2 | 0 | 0 | $0.00635575 | $0.00859970 | pass |

最终确认汇总：

| Metric | Value |
|---|---:|
| Runs below legacy | 2 / 4 |
| Total searches | 51 |
| Total pre-edit searches | 25 |
| Total `rtc_read` | 1 |
| Redundant `rtc_read` | 1 |
| Native reads | 3 |
| Total tokens | 11,772,898 |
| Total cost | $0.09857317 |
| Total legacy target | $0.05498075 |
| Delta vs legacy | +$0.04359242 |

## 结论

当前 prompt 是已经测试过的最强 prompt-only 版本，但仅靠 prompt 对 OpenClaw 的约束并不可靠。它可以产生不错的单次运行，但重跑时模型仍可能进入 search spiral、冗余 `rtc_read` 或 native `read`。

下一步建议：在 OpenClaw 插件中增加 runtime/tool enforcement，而不是继续堆 prompt 文本。有效约束点包括：

- RTC SWE 运行期间隐藏或阻止对仓库 source/docs 的 native `read`；
- 当同文件 RTC snippets 已存在时阻止 `rtc_read`；
- 对每个任务过量 `rtc_search_code` 调用进行限制或警告；
- 在较小的有界重试次数后停止 post-edit repair loops。
