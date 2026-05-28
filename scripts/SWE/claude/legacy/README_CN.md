# SWE Lite 纯 Claude 运行器

本目录用纯 Claude Code 运行同一个 SWE-bench Lite 任务流程。

它不会加载 Retrieval Token Cutter 插件，也不会启动 RTC、AGFS 或 MCP 服务。

使用默认本地验证路径前，请先从仓库根目录安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

默认推导出的本地 SWE-bench 环境使用 Conda。设置 `SWE_USE_DERIVED_LOCAL_ENV=0` 可跳过本地环境推导进行冒烟运行；设置 `SWE_SKIP_VALIDATION=1` 可跳过最终验证。

## 运行

从仓库根目录执行：

```bash
source scripts/SWE/claude/legacy/setup_swe_env.sh
SWE_USE_DERIVED_LOCAL_ENV=0 \
SWE_SKIP_VALIDATION=1 \
./scripts/SWE/claude/legacy/run_swe_task_lite_plain_claude.sh
```

运行其他 SWE-bench Lite instance：

```bash
./scripts/SWE/claude/legacy/run_swe_task_lite_plain_claude.sh <instance_id>
```

## 输出

运行输出位于：

```text
scripts/SWE/claude/legacy/output_logs/<timestamp>-swe-lite-plain-r<run>-p<pid>/
```

设置 `SWE_OUTPUT_ROOT=/path/to/output_logs` 可写入其他目录。

常用文件：

- `workspace/TASK.md`
- `logs/claude-code-debug.log`
- `logs/claude-stdout.log`
- `logs/<claude-session>.jsonl`
- `latest_session_render.txt`
- `validation.md`
- `validation.json`
