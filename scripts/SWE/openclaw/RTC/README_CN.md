# SWE Lite OpenClaw RTC 运行器

本运行器使用 OpenClaw 和 Retrieval Token Cutter OpenClaw 插件执行一个 SWE-bench Lite 任务。

它会：

- 解析 SWE-bench Lite instance；
- 克隆并重置 benchmark 仓库；
- 推导本地 SWE-bench 验证环境；
- 链接并启用 `openclaw-plugin/`；
- 非交互式运行 `openclaw agent --local`；
- 验证 OpenClaw 实际调用了 `rtc_search_code` 和 `rtc_edit_file`；
- 执行附加验证；
- 将日志、渲染后的 session 文本、AGFS/RTC 运行时数据和验证输出写入 `output_logs/`。

## 要求

从仓库根目录安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

OpenClaw 必须已经配置好可用模型 provider。默认模型为：

```bash
export OPENCLAW_MODEL="${OPENCLAW_MODEL:-deepseek/deepseek-v4-flash}"
```

embedding 凭据应保存在 shell 环境中，不要写入仓库：

```bash
export RTC_EMBEDDING_API_KEY="<your-key>"
export RTC_EMBEDDING_BASE_URL="https://api.openai-proxy.org"
export RTC_EMBEDDING_MODEL="text-embedding-3-small"
```

默认不强制 embedding 预检。即使 OpenAI-compatible endpoint 不暴露 `/v1/embeddings`，RTC 搜索仍可使用 BM25/ctags fallback。设置 `RTC_EMBEDDING_PROBE_REQUIRED=1` 可在 embedding endpoint 有问题时快速失败。

## 运行

从仓库根目录执行：

```bash
source scripts/SWE/openclaw/RTC/setup_swe_env.sh
./scripts/SWE/openclaw/RTC/run_swe_task_lite_openclaw_rtc_plugin.sh
```

默认任务：

```bash
pallets__flask-4045
```

运行其他任务：

```bash
./scripts/SWE/openclaw/RTC/run_swe_task_lite_openclaw_rtc_plugin.sh django__django-11133
```

## 验证

默认 `SWE_VALIDATION_FORCE_LOCAL=1`，验证使用从官方 SWE-bench `TestSpec` 推导出的任务本地环境。

尝试官方 Docker harness：

```bash
SWE_VALIDATION_FORCE_LOCAL=0 ./scripts/SWE/openclaw/RTC/run_swe_task_lite_openclaw_rtc_plugin.sh
```

## 输出

每次运行写入：

```text
scripts/SWE/openclaw/RTC/output_logs/<timestamp>-swe-lite-openclaw-rtc-r<run>-p<pid>/
```

常用文件：

- `workspace/`：OpenClaw 编辑后的任务 checkout。
- `TASK.md`：发送给 OpenClaw 的 prompt。
- `logs/openclaw-stdout.log`：OpenClaw 非交互输出。
- `logs/openclaw-agent.json`：同一输出的 JSON 捕获，便于调试。
- `logs/openclaw-plugin-runtime.json`：插件 runtime inspection。
- `latest_session_render.txt`：可读 session 摘要。
- `openclaw_tool_summary.json`：解析后的工具调用摘要。
- `validation.md`：人类可读验证结果。
- `validation.json`：机器可读验证结果。
- `logs/validation-summary.json`：validator 原始 stdout。
- `logs/validation-stderr.log`：validator stderr。

`output_logs/latest` 指向最新运行。

## 确认 RTC 工具使用

如果 OpenClaw session JSONL 中没有同时出现以下工具，运行器会失败：

```text
rtc_search_code
rtc_edit_file
```

手动检查：

```bash
cat scripts/SWE/openclaw/RTC/output_logs/latest/openclaw_tool_summary.json
rg -n "rtc_search_code|rtc_edit_file" scripts/SWE/openclaw/RTC/output_logs/latest/logs/*.jsonl
```

## 说明

运行器每次都会把 OpenClaw 插件作为 linked local plugin 安装：

```bash
openclaw plugins install --link ./openclaw-plugin --dangerously-force-unsafe-install
openclaw plugins enable retrieval-token-cutter
```

运行器会先卸载已有的 `retrieval-token-cutter` 注册，再安装当前 checkout 的 linked plugin，避免其他 checkout 的旧注册影响本次运行。

`--dangerously-force-unsafe-install` 是预期行为，因为插件会通过 Node child process API 启动本地 RTC/AGFS 进程。
