# SWE Lite Claude RTC-FILTER 插件运行器

本目录运行一个 SWE-bench Lite 任务，并在 Claude Code 中加载 `claude-plugin/`，同时启用 RTC 过滤流程。

整体流程：

- 解析 SWE-bench Lite instance；
- 克隆目标仓库并切到 base commit；
- 写入 `TASK.md`；
- 为本次运行启动隔离的 RTC/AGFS 后端；
- 启动 Claude Code；
- 渲染 Claude transcript；
- 默认执行本地附加验证。

## 前置检查

从仓库根目录准备 Python 依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

如果使用 `uv`，建议安装运行器需要的 extras：

```bash
uv sync --extra mcp --extra swe
```

本地 SWE-bench 环境推导依赖 Conda，因为脚本会适配官方 SWE-bench `TestSpec` 中的环境命令。确认 Conda 可用：

```bash
conda info --base
```

如果是新的 Anaconda/Miniconda 安装，可能需要先接受默认 channel 的 ToS：

```bash
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
```

确认 Claude Code 已登录：

```bash
claude --print "hello"
```

如果没有可用的 `agfs-server`，先构建本仓库内置版本：

```bash
(cd agfs && make build)
```

从模板创建本地 `env.sh`，然后编辑里面的本地配置，不要提交真实密钥：

```bash
./bootstrap.sh --skip-python --skip-agfs
$EDITOR env.sh
```

实际使用 RTC 代码搜索时，至少需要设置 `RTC_EMBEDDING_API_KEY`。如果
`agfs-server` 不在 `PATH` 中，也可以在 `env.sh` 里设置 `AGFS_BIN`。

## 运行

从仓库根目录运行：

```bash
cd /path/to/retrieval-token-cutter
source scripts/SWE/claude/RTC-FILTER/setup_swe_env.sh
./scripts/SWE/claude/RTC-FILTER/run_swe_task_lite_rtc_plugin.sh
```

默认任务是：

```text
pallets__flask-4045
```

运行其他 SWE-bench Lite 任务：

```bash
./scripts/SWE/claude/RTC-FILTER/run_swe_task_lite_rtc_plugin.sh django__django-11133
```

默认 `SWE_VALIDATION_FORCE_LOCAL=1`，因此验证会使用从 SWE-bench `TestSpec` 推导出的任务本地环境。这能避免 Docker 内部无法访问 GitHub 的网络问题。

若想尝试官方 Docker harness：

```bash
SWE_VALIDATION_FORCE_LOCAL=0 ./scripts/SWE/claude/RTC-FILTER/run_swe_task_lite_rtc_plugin.sh
```

快速冒烟运行：

```bash
SWE_USE_DERIVED_LOCAL_ENV=0 \
SWE_SKIP_VALIDATION=1 \
./scripts/SWE/claude/RTC-FILTER/run_swe_task_lite_rtc_plugin.sh
```

## 输出

运行输出位于：

```text
scripts/SWE/claude/RTC-FILTER/output_logs/<timestamp>-swe-lite-rtc-r<run>-p<pid>/
```

最新运行链接：

```text
scripts/SWE/claude/RTC-FILTER/output_logs/latest
```

常用文件：

- `workspace/TASK.md`
- `logs/claude-code-debug.log`
- `logs/claude-stdout.log`
- `logs/agfs-server.log`
- `logs/retrieval-token-cutter-server.log`
- `latest_session_render.txt`
- `produced.patch`
- `validation.md`
- `validation.json`

验证结束后，`workspace/.git` 会移动到同级 `workspace.git`，保留生成 checkout 的分析价值，同时避免编辑器把每次 SWE 输出都识别为嵌套 Git 仓库。

## 检查插件和工具调用

确认插件加载：

```bash
rg -n "Skill prompt|Loaded hooks|plugin:retrieval-token-cutter" scripts/SWE/claude/RTC-FILTER/output_logs/latest/logs/claude-code-debug.log
```

确认发生 RTC MCP 调用：

```bash
rg -n "mcp__plugin_retrieval-token-cutter_retrieval-token-cutter__(search_code|edit_file)|Tool 'search_code'|Tool 'edit_file'" scripts/SWE/claude/RTC-FILTER/output_logs/latest/logs/claude-code-debug.log
```
