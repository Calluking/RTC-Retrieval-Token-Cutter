# Retrieval Token Cutter

让 Claude Code 或 OpenClaw 通过 Retrieval Token Cutter 语义代码搜索和精确替换编辑来理解并修改本地代码库。

[English README](README.md)

## 功能

- 从 `claude-plugin/` 加载本地 `retrieval-token-cutter` Claude Code 插件。
- 从 `openclaw-plugin/` 加载原生 OpenClaw 插件。
- Claude 需要时自动启动 MCP bridge、AGFS 和 Retrieval Token Cutter 后端。
- OpenClaw 加载插件时自动启动本地 AGFS 和 Retrieval Token Cutter 后端。
- 对代码相关 prompt 自动注入代码搜索/编辑策略。
- 提供代码搜索和精确文件编辑工具。
- 宿主退出后自动停止由插件启动的服务。

## 环境要求

- Python 3.11+
- Claude Code CLI、OpenClaw CLI，或两者都安装
- `agfs-server`，需要在 `PATH` 中，或构建在 `agfs/build/agfs-server`
- Go 1.21+，如果要从本仓库构建内置 AGFS server
- OpenAI 兼容的 embedding endpoint 和 API key
- Conda，如果使用 SWE runner 默认的任务专用本地验证环境
- `requirements.txt` 已包含 `httpx[socks]`，支持 SOCKS proxy URL；`setup_env.sh` 也会为 `127.0.0.1`、`localhost` 和 `::1` 设置 `NO_PROXY`/`no_proxy`，避免本地 RTC/AGFS 请求走 HTTP(S)/SOCKS 代理。

安装 Python 依赖：

```bash
cd /path/to/retrieval-token-cutter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

如果 `agfs-server` 不在 `PATH` 中，可以构建仓库内置版本：

```bash
(cd agfs && make build)
```

如果使用 `uv`，安装插件和 SWE runner 需要的 extras：

```bash
uv sync --extra mcp --extra swe
```

## 配置

先从 [env.sh.example](env.sh.example) 创建本地 `env.sh`，然后编辑里面的本地配置：

```bash
cp env.sh.example env.sh
$EDITOR env.sh
```

实际做代码搜索时，至少要设置 `RTC_EMBEDDING_API_KEY`。如果不使用仓库里的
`.venv`，请把 `PY_BIN` 指向能 import `flask`、`mcp`、`openai` 和
`pyagfs` 的 Python。Claude 插件启动器也会检查常见本地 Conda 路径，例如
`~/miniconda3/bin/python`。

不要把真实 API key 提交到公开仓库。

## 启动 Claude

在你希望 Claude 修改的项目目录中运行：

```bash
cd /path/to/project
claude --plugin-dir /path/to/retrieval-token-cutter/claude-plugin
```

不要传 `--mcp-config`，插件自带 `.mcp.json`。插件会先启动自己的 MCP
server，RTC/AGFS 后端会在需要时按需启动。如果环境变量只写在 `env.sh`
里，请改用 helper 启动器：

```bash
cd /path/to/project
/path/to/retrieval-token-cutter/claude-plugin/bin/rtc-claude
```

然后在 Claude 里直接说：

```text
Fix the bug in the add function
```

对看起来像代码任务的请求，插件会自动注入 MCP 工作流策略。

## 启动 OpenClaw

先在本仓库中安装一次 OpenClaw 本地链接插件：

```bash
cd /path/to/retrieval-token-cutter
source setup_env.sh
openclaw plugins install --link ./openclaw-plugin --dangerously-force-unsafe-install
openclaw plugins enable retrieval-token-cutter
openclaw gateway restart
```

如果之前已经从另一个 checkout 安装过这个插件，先卸载旧的注册项，让
OpenClaw 重新链接到当前 clone：

```bash
openclaw plugins uninstall retrieval-token-cutter --force
openclaw plugins install --link ./openclaw-plugin --dangerously-force-unsafe-install
```

OpenClaw 要求 `--dangerously-force-unsafe-install`，因为这个插件会通过 Node child process API 自动启动本地 RTC/AGFS 进程。

在你希望 OpenClaw 修改的项目目录中，用新的本地 TUI session 启动：

```bash
cd /path/to/project
source /path/to/retrieval-token-cutter/setup_env.sh
export RTC_WORKSPACE_ROOT="$PWD"
openclaw chat --local --session "rtc-$(date +%s)"
```

`openclaw chat` 是官方 local embedded TUI 入口，等价于 `openclaw tui --local`。加上新的 `--session` 可以避免复用默认的 `agent:<agent>:main` 历史。

然后直接输入：

```text
Fix the bug in the add function.
```

## 验证

在 Claude 里运行：

```text
/plugin
```

应该能看到：

```text
retrieval-token-cutter Plugin · inline · ✔ enabled
└ retrieval-token-cutter MCP · ✔ connected
```

Claude Code debug log 中应出现类似工具调用：

```text
mcp__plugin_retrieval-token-cutter_retrieval-token-cutter__search_code
mcp__plugin_retrieval-token-cutter_retrieval-token-cutter__edit_file
```

对于 OpenClaw，先验证插件已经加载：

```bash
openclaw plugins inspect retrieval-token-cutter --runtime --json
```

运行时输出中应包含：

```text
rtc_health
rtc_index_codebase
rtc_search_code
rtc_edit_file
```

如果要确认某次运行确实用了搜索，可以查看最新 session log：

```bash
latest=$(ls -t ~/.openclaw/agents/*/sessions/*.jsonl | grep -v trajectory | head -1)
rg -n "rtc_search_code|rtc_edit_file|python -m pytest|Fix the bug" "$latest"
```

## 重要文件

- [env.sh.example](env.sh.example)：本地环境配置模板。复制为已被 git 忽略的 `env.sh`。
- [setup_env.sh](setup_env.sh)：启动 Claude 前 source 的设置脚本。
- [claude-plugin/](claude-plugin/)：本地 Claude Code 插件。
- [openclaw-plugin/](openclaw-plugin/)：原生 OpenClaw 插件。
- [claude-plugin/prompts/code_policy_injection.txt](claude-plugin/prompts/code_policy_injection.txt)：自动注入的 MCP 代码策略。
- [openclaw-plugin/prompts/code_policy_injection.txt](openclaw-plugin/prompts/code_policy_injection.txt)：自动注入的 OpenClaw 代码策略。
- [scripts/SWE/claude/RTC/](scripts/SWE/claude/RTC/)：基于 Retrieval Token Cutter 插件的 SWE Lite runner。
- [scripts/SWE/claude/legacy/](scripts/SWE/claude/legacy/)：不加载插件的 plain Claude SWE Lite runner。
- [scripts/SWE/openclaw/RTC/](scripts/SWE/openclaw/RTC/)：基于 Retrieval Token Cutter OpenClaw 插件的 SWE Lite runner。
- [scripts/SWE/openclaw/legacy/](scripts/SWE/openclaw/legacy/)：不加载插件的 plain OpenClaw SWE Lite runner。

## SWE Lite Runner

SWE runner 会生成任务提示词，并以非交互方式启动 Claude 或 OpenClaw。

Claude legacy：

```bash
source scripts/SWE/claude/legacy/setup_swe_env.sh
./scripts/SWE/claude/legacy/run_swe_task_lite_plain_claude.sh
```

Claude RTC/plugin：

```bash
source scripts/SWE/claude/RTC/setup_swe_env.sh
./scripts/SWE/claude/RTC/run_swe_task_lite_rtc_plugin.sh
```

OpenClaw legacy：

```bash
source scripts/SWE/openclaw/legacy/setup_swe_env.sh
./scripts/SWE/openclaw/legacy/run_swe_task_lite_plain_openclaw.sh
```

OpenClaw RTC/plugin：

```bash
source scripts/SWE/openclaw/RTC/setup_swe_env.sh
./scripts/SWE/openclaw/RTC/run_swe_task_lite_openclaw_rtc_plugin.sh
```

更多说明见 [scripts/SWE/claude/RTC/README.md](scripts/SWE/claude/RTC/README.md)、[scripts/SWE/claude/legacy/README.md](scripts/SWE/claude/legacy/README.md)、[scripts/SWE/openclaw/RTC/README.md](scripts/SWE/openclaw/RTC/README.md) 和 [scripts/SWE/openclaw/legacy/README.md](scripts/SWE/openclaw/legacy/README.md)。

默认情况下，`scripts/SWE/claude/RTC/setup_swe_env.sh` 会设置 `SWE_VALIDATION_FORCE_LOCAL=1`。验证会在为任务派生出的本地 SWE-bench 环境中运行，而不是官方 Docker harness；这可以避开容器无法访问 GitHub 的网络问题。本地路径会根据 SWE-bench `TestSpec` 派生命令并应用 benchmark test patch，但官方 Docker harness 仍然是更严格的最终行为。设置 `SWE_VALIDATION_FORCE_LOCAL=0` 可以改用官方 Docker harness。

## 说明

生成数据不会进入 git。RTC SWE runner 会把方便分析的运行输出保留在 `scripts/SWE/claude/RTC/output_logs/`，包括 AGFS 数据和渲染后的 transcript；可复用的仓库 clone 缓存在项目外的 `${XDG_CACHE_HOME:-~/.cache}/retrieval-token-cutter/swe/rtc/cache/repo`。验证结束后，生成 workspace 里的 Git 元数据会被移到旁边，避免编辑器把每次 SWE 运行都显示成嵌套 Git 仓库。
