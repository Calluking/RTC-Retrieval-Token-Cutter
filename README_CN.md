# Retrieval Token Cutter Claude 插件

让 Claude Code 通过 Retrieval Token Cutter 语义代码搜索、MCP 工具和本地 Claude 插件理解并修改本地代码库。

[English README](README.md)

## 功能

- 从 `claude-plugin/` 加载本地 `retrieval-token-cutter` Claude Code 插件。
- Claude 需要时自动启动 MCP bridge、AGFS 和 Retrieval Token Cutter 后端，并在 Claude 退出时停止它们。
- 自动注入 `claude-plugin/prompts/code_policy_injection.txt` 中的代码搜索/编辑策略。
- 提供代码搜索和 MCP 文件编辑工具。
- Claude 退出后自动停止由插件启动的后端服务。

## 环境要求

- Python 3.11+
- Claude Code CLI
- `agfs-server`，需要在 `PATH` 中，或构建在 `agfs/build/agfs-server`
- OpenAI 兼容的 embedding endpoint 和 API key
- Conda，如果使用 SWE runner 默认的任务专用本地验证环境
- `requirements.txt` 已包含 `httpx[socks]`，支持 SOCKS proxy URL；`setup_env.sh` 也会为 `127.0.0.1`、`localhost` 和 `::1` 设置 `NO_PROXY`/`no_proxy`，避免本地 RTC/AGFS 请求走 HTTP(S)/SOCKS 代理。

安装 Python 依赖：

```bash
cd /path/to/retrieval-token-cutter-claude-plugin
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

如果使用 `uv`，安装插件和 SWE runner 需要的 extras：

```bash
uv sync --extra mcp --extra swe
```

## 配置

运行 Claude 前，先从 [env.sh.example](env.sh.example) 创建本地 `env.sh`：

```bash
cp env.sh.example env.sh
export RTC_EMBEDDING_API_KEY="<your-key>"
export RTC_EMBEDDING_BASE_URL="https://api.openai.com"
export RTC_EMBEDDING_MODEL="text-embedding-3-large"
```

如果使用上面的 `.venv`，`PY_BIN` 可以留空，`setup_env.sh` 会自动找到 `.venv/bin/python`。

不要把真实 API key 提交到公开仓库。

## 启动 Claude

在你希望 Claude 修改的项目目录中运行三行命令：

```bash
cd /path/to/project
source /path/to/retrieval-token-cutter-claude-plugin/setup_env.sh
claude --plugin-dir "$RTC_CLAUDE_PLUGIN_DIR"
```

然后在 Claude 里直接说：

```text
Fix the bug in the add function
```

对看起来像代码任务的请求，插件会自动注入 MCP 工作流策略。

## 验证

在 Claude 里运行：

```text
/plugin
```

应该能看到 `retrieval-token-cutter`，并且没有加载错误。

Claude Code debug log 中应出现类似工具调用：

```text
mcp__plugin_retrieval-token-cutter_retrieval-token-cutter__search_code
mcp__plugin_retrieval-token-cutter_retrieval-token-cutter__edit_file
```

## 重要文件

- [env.sh.example](env.sh.example)：本地环境配置模板。复制为已被 git 忽略的 `env.sh`。
- [setup_env.sh](setup_env.sh)：启动 Claude 前 source 的设置脚本。
- [claude-plugin/](claude-plugin/)：本地 Claude Code 插件。
- [claude-plugin/prompts/code_policy_injection.txt](claude-plugin/prompts/code_policy_injection.txt)：自动注入的 MCP 代码策略。
- [scripts/SWE/claude/RTC/](scripts/SWE/claude/RTC/)：基于 Retrieval Token Cutter 插件的 SWE Lite runner。
- [scripts/SWE/claude/legacy/](scripts/SWE/claude/legacy/)：不加载插件的 plain Claude SWE Lite runner。

## SWE Lite Runner

SWE runner 会生成任务提示词，并用 print mode 启动 Claude：

```bash
source scripts/SWE/claude/RTC/setup_swe_env.sh
./scripts/SWE/claude/RTC/run_swe_task_lite_rtc_plugin.sh
```

更多说明见 [scripts/SWE/claude/RTC/README.md](scripts/SWE/claude/RTC/README.md) 和 [scripts/SWE/claude/legacy/README.md](scripts/SWE/claude/legacy/README.md)。

默认情况下，`scripts/SWE/claude/RTC/setup_swe_env.sh` 会设置 `SWE_VALIDATION_FORCE_LOCAL=1`。验证会在为任务派生出的本地 SWE-bench 环境中运行，而不是官方 Docker harness；这可以避开容器无法访问 GitHub 的网络问题。本地路径会根据 SWE-bench `TestSpec` 派生命令并应用 benchmark test patch，但官方 Docker harness 仍然是更严格的最终行为。设置 `SWE_VALIDATION_FORCE_LOCAL=0` 可以改用官方 Docker harness。

## 说明

生成数据不会进入 git。RTC SWE runner 会把方便分析的运行输出保留在 `scripts/SWE/claude/RTC/output_logs/`，包括 AGFS 数据和渲染后的 transcript；可复用的仓库 clone 缓存在项目外的 `${XDG_CACHE_HOME:-~/.cache}/retrieval-token-cutter/swe/rtc/cache/repo`。验证结束后，生成 workspace 里的 Git 元数据会被移到旁边，避免编辑器把每次 SWE 运行都显示成嵌套 Git 仓库。
