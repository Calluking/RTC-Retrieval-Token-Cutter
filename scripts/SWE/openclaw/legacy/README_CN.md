# SWE Lite OpenClaw Legacy 运行器

本目录用纯 OpenClaw 运行同一个 SWE-bench Lite 任务流程。

它不会加载 Retrieval Token Cutter 插件，也不会启动 RTC、AGFS、MCP 或插件托管服务。

如果个人 OpenClaw 配置启用了本地插件，运行器会在运行期间临时清空本地插件加载路径、禁用 RTC 插件条目，并把 `plugins.allow` 设置为当前模型 provider。退出时会恢复原配置。

使用默认本地验证路径前，请从仓库根目录安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

OpenClaw 必须已经配置好可用模型 provider。默认模型为：

```bash
export OPENCLAW_MODEL="${OPENCLAW_MODEL:-deepseek/deepseek-v4-flash}"
```

## 运行

从仓库根目录执行：

```bash
source scripts/SWE/openclaw/legacy/setup_swe_env.sh
./scripts/SWE/openclaw/legacy/run_swe_task_lite_plain_openclaw.sh
```

默认任务：

```bash
pallets__flask-4045
```

运行其他任务：

```bash
./scripts/SWE/openclaw/legacy/run_swe_task_lite_plain_openclaw.sh django__django-11133
```

## 验证

默认 `SWE_VALIDATION_FORCE_LOCAL=1`，验证使用从官方 SWE-bench `TestSpec` 推导出的任务本地环境。

快速冒烟测试可设置 `SWE_SKIP_VALIDATION=1` 跳过最终验证。

## 输出

运行输出位于：

```text
scripts/SWE/openclaw/legacy/output_logs/<timestamp>-swe-lite-openclaw-plain-r<run>-p<pid>/
```

设置 `SWE_OUTPUT_ROOT=/path/to/output_logs` 可写入其他目录。

常用文件：

- `workspace/TASK.md`
- `logs/openclaw-stdout.log`
- `logs/openclaw-agent.json`
- `logs/<openclaw-session>.jsonl`
- `latest_session_render.txt`
- `openclaw_tool_summary.json`
- `validation.md`
- `validation.json`
