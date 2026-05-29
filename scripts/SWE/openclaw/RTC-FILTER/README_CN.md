# SWE Lite OpenClaw RTC-FILTER 运行器

这是 `scripts/SWE/claude/RTC-FILTER` 的 OpenClaw 对应版本。它复用
`../RTC` 的 OpenClaw RTC plugin harness，但使用独立的 cache/output 命名空间，
并默认开启过滤策略 prompt。

默认开启：

- `RTC_INJECT_FILTERING_PROMPT=1`
- `RTC_FILTER_ENABLED=1`
- `RTC_FILTER_NATIVE_READ=1`
- `RTC_FILTER_NATIVE_BASH=1`

原生 `read` 和 `exec` 的过滤逻辑在 `openclaw-plugin/src/filter.ts` 中实现。
prompt 注入通过 `openclaw-plugin/src/policy.ts` 渲染，因此过滤策略说明与
Claude 插件使用同一套环境变量开关行为。

## 运行

从仓库根目录执行：

```bash
source scripts/SWE/openclaw/RTC-FILTER/setup_swe_env.sh
./scripts/SWE/openclaw/RTC-FILTER/run_swe_task_lite_openclaw_rtc_filter_plugin.sh
```

运行指定 SWE-bench Lite 任务：

```bash
./scripts/SWE/openclaw/RTC-FILTER/run_swe_task_lite_openclaw_rtc_filter_plugin.sh django__django-11019
```

更快的 smoke/debug 运行：

```bash
SWE_USE_DERIVED_LOCAL_ENV=0 \
SWE_SKIP_VALIDATION=1 \
./scripts/SWE/openclaw/RTC-FILTER/run_swe_task_lite_openclaw_rtc_filter_plugin.sh django__django-11019
```

## 输出

每次运行写入：

```text
scripts/SWE/openclaw/RTC-FILTER/output_logs/<timestamp>-swe-lite-openclaw-rtc-r<run>-p<pid>/
```

常用文件：

- `workspace/TASK.md`：发送给 OpenClaw 的 prompt，包含过滤策略段落。
- `latest_session_render.txt`：可读 session 摘要。
- `openclaw_tool_summary.json`：解析后的工具调用摘要。
- `logs/openclaw-stdout.log`：OpenClaw 非交互输出。
- `logs/openclaw-plugin-runtime.json`：插件 runtime inspection。

`output_logs/latest` 指向最新运行。

## 与 RTC 的关系

本目录有意包装 `../RTC/run_swe_task_lite_openclaw_rtc_plugin.sh`，而不是复制整套
harness。这样 OpenClaw RTC 和 RTC-FILTER 的行为保持一致，同时在路径、文档和默认
环境变量上明确区分实验模式。
