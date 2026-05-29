# SWE Lite Claude RTC 插件运行器

本目录运行 SWE-bench Lite 任务，并在 Claude Code 中加载 `claude-plugin/`。运行器会在 Claude 开始前为本次运行启动隔离的 RTC/AGFS 后端，然后禁止 Claude 进程内的插件自动启动路径，确保 MCP 调用使用同一个后端实例。

流程包括：

- 解析 SWE-bench Lite instance；
- 克隆目标仓库到 base commit；
- 写入 `TASK.md`；
- 启动 Claude Code；
- 渲染 Claude transcript；
- 可选执行验证。

## 设置

从仓库根目录安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

如果使用 `uv`：

```bash
uv sync --extra mcp --extra swe
```

用 bootstrap 创建本地 `env.sh`，然后编辑里面的本地配置：

```bash
./bootstrap.sh --skip-python --skip-agfs
$EDITOR env.sh
```

实际使用 RTC 代码搜索时，至少需要设置 `RTC_EMBEDDING_API_KEY`。

默认本地 SWE-bench 环境推导依赖 Conda，因为脚本会适配官方 `TestSpec` 环境命令。

## 运行

```bash
cd /path/to/retrieval-token-cutter
source scripts/SWE/claude/RTC/setup_swe_env.sh
./scripts/SWE/claude/RTC/run_swe_task_lite_rtc_plugin.sh
```

默认 `setup_swe_env.sh` 设置 `SWE_VALIDATION_FORCE_LOCAL=1`，验证会在为任务创建的本地 SWE-bench 环境中执行。若要使用官方 Docker harness：

```bash
SWE_VALIDATION_FORCE_LOCAL=0 ./scripts/SWE/claude/RTC/run_swe_task_lite_rtc_plugin.sh
```

Claude 修复循环期间，运行器会在 `workspace/RUN_IN_SWE_LOCAL_ENV.sh` 创建任务本地环境 helper：

```bash
./RUN_IN_SWE_LOCAL_ENV.sh pytest -q <target>
./RUN_IN_SWE_LOCAL_ENV.sh --reinstall pytest -q <target>
```

如果设置了 HTTP(S) 或 SOCKS 代理，运行器会为 loopback 地址强制设置 `NO_PROXY`/`no_proxy`，确保 Claude、RTC 和 AGFS 可以通过 `127.0.0.1` 通信。

快速冒烟运行：

```bash
cd /path/to/retrieval-token-cutter
source scripts/SWE/claude/RTC/setup_swe_env.sh
SWE_USE_DERIVED_LOCAL_ENV=0 \
SWE_SKIP_VALIDATION=1 \
./scripts/SWE/claude/RTC/run_swe_task_lite_rtc_plugin.sh
```

## 输出

运行目录：

```text
scripts/SWE/claude/RTC/output_logs/<timestamp>-swe-lite-rtc-r<run>-p<pid>/
```

最新运行链接：

```text
scripts/SWE/claude/RTC/output_logs/latest
```

常用文件：

- `workspace/TASK.md`
- `agfs-data/`
- `logs/claude-code-debug.log`
- `logs/claude-stdout.log`
- `logs/agfs-server.log`
- `logs/retrieval-token-cutter-server.log`
- `latest_session_render.txt`
- `validation.md`
- `validation.json`

验证后，`workspace/.git` 会移动为同级 `workspace.git`，便于保留运行现场又避免编辑器展示大量嵌套仓库。

## 检查

确认插件加载：

```bash
rg -n "Skill prompt|Loaded hooks|plugin:retrieval-token-cutter" "${SWE_OUTPUT_ROOT:-scripts/SWE/claude/RTC/output_logs}/latest/logs/claude-code-debug.log"
```

确认 MCP 调用：

```bash
rg -n "mcp__plugin_retrieval-token-cutter_retrieval-token-cutter__(search_code|edit_file)|Tool 'search_code'|Tool 'edit_file'" "${SWE_OUTPUT_ROOT:-scripts/SWE/claude/RTC/output_logs}/latest/logs/claude-code-debug.log"
```
