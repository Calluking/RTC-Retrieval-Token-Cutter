<p align="center">
  <img src="docs/assets/readme/RTC/LOGO_BACKGROUND.png" alt="Retrieval Token Cutter" width="760">
</p>

# Retrieval Token Cutter

<p align="center">
  <a href="LICENSE"><img alt="许可证" src="https://img.shields.io/badge/license-MulanPSL--2.0-blue.svg"></a>
  <a href="pyproject.toml"><img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-blue.svg"></a>
  <a href="pyproject.toml"><img alt="版本" src="https://img.shields.io/badge/version-0.1.0-blue.svg"></a>
  <a href="claude-plugin/"><img alt="Claude Code" src="https://img.shields.io/badge/Claude%20Code-plugin-purple.svg"></a>
  <a href="openclaw-plugin/"><img alt="OpenClaw" src="https://img.shields.io/badge/OpenClaw-plugin-blue.svg"></a>
  <a href="filter/"><img alt="RTC 过滤" src="https://img.shields.io/badge/filter-read%20%2B%20bash-orange.svg"></a>
  <a href="agfs/"><img alt="AGFS" src="https://img.shields.io/badge/AGFS-local%20memory-teal.svg"></a>
</p>

让 Claude Code 或 OpenClaw 通过 Retrieval Token Cutter 语义代码搜索、长输出过滤和精确替换编辑来理解并修改本地代码库。

[English README](README.md)

## 概览

Retrieval Token Cutter 提供两个本地插件：

| 宿主 | 插件 | 能力 |
| --- | --- | --- |
| Claude Code | [claude-plugin/](claude-plugin/) | MCP 代码搜索/编辑工具，以及 prompt 策略注入 |
| OpenClaw | [openclaw-plugin/](openclaw-plugin/) | 原生工具、prompt 策略注入，以及 read/exec 过滤 |

两个插件都可以自动启动本地 Retrieval Token Cutter 后端和 AGFS 服务，并在宿主退出时停止自己启动的服务。

![运行架构](<docs/assets/readme/RTC/CN_Runtime Architecture.png>)

## 环境要求

- Python 3.11+
- Go 1.21+
- Claude Code CLI、OpenClaw CLI，或两者都安装并已登录
- OpenAI 兼容的 embedding endpoint 和 API key
- Conda，仅在使用 SWE runner 默认本地验证环境时需要

## 快速开始

在全新 checkout 中先准备一次：

```bash
cd /path/to/retrieval-token-cutter
./bootstrap.sh
$EDITOR env.sh
```

至少在 `env.sh` 中设置：

```bash
export RTC_EMBEDDING_API_KEY="<your-key>"
```

`./bootstrap.sh` 会创建 `.venv`、安装 `requirements.txt`、在缺少时创建
`env.sh`，并构建 `agfs/build/agfs-server`。

![全新 clone 快速开始](<docs/assets/readme/RTC/CN_Fresh Clone Start.png>)

常用变体：

```bash
./bootstrap.sh --help
./bootstrap.sh --force-agfs
./bootstrap.sh --install-openclaw-plugin
```

如果想手动执行同样的步骤：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp env.sh.example env.sh
make -C agfs build
```

## 启动 Claude

在你希望 Claude 修改的项目目录中运行：

```bash
cd /path/to/project
/path/to/retrieval-token-cutter/claude-plugin/bin/rtc-claude
```

这个 helper 会加载 `env.sh`，再带上插件目录启动 Claude。如果你的 shell 已经导出了同样的 RTC 环境变量，也可以直接运行：

```bash
cd /path/to/project
claude --plugin-dir /path/to/retrieval-token-cutter/claude-plugin
```

不要传 `--mcp-config`；Claude 插件自带 `.mcp.json`。

## 启动 OpenClaw

先安装一次本地链接插件：

```bash
cd /path/to/retrieval-token-cutter
./bootstrap.sh --install-openclaw-plugin
```

等价的手动命令：

```bash
openclaw plugins install --link ./openclaw-plugin --dangerously-force-unsafe-install
openclaw plugins enable retrieval-token-cutter
openclaw gateway restart
```

OpenClaw 要求 `--dangerously-force-unsafe-install`，因为这个插件会通过 Node child process API 自动启动本地 RTC/AGFS 进程。

然后在你希望 OpenClaw 修改的项目目录中启动：

```bash
cd /path/to/project
openclaw chat --local
```

正常交互使用时不需要 `source setup_env.sh`，也不需要设置 `RTC_DIR`、
`RTC_RUNTIME_DIR` 或 `RTC_WORKSPACE_ROOT`。本地链接插件会自动发现当前仓库、
加载 `env.sh`、启动 RTC/AGFS，并把启动 OpenClaw 的目录作为 workspace。

## 验证

Claude：

```text
/plugin
```

预期状态：

```text
retrieval-token-cutter Plugin · inline · ✔ enabled
└ retrieval-token-cutter MCP · ✔ connected
```

OpenClaw：

```bash
openclaw plugins inspect retrieval-token-cutter --runtime --json
```

运行时输出应包含：

```text
rtc_health
rtc_index_codebase
rtc_search_code
rtc_edit_file
```

如果要确认某次运行确实用了 RTC 搜索/过滤：

```bash
latest=$(ls -t ~/.openclaw/agents/*/sessions/*.jsonl | grep -v trajectory | head -1)
rg -n "Retrieval Token Cutter|FILTER IS TRIGGERED|rtc_search_code|rtc_edit_file" "$latest"
```

对于 Claude，可以查看当前 Claude debug log 或 `/plugin` 面板。健康的代码任务应出现包含 `search_code` 和 `edit_file` 的 MCP 工具名。

![代码任务流程](<docs/assets/readme/RTC/CN_Code Task Flow.png>)

## 配置

本地配置放在被 git 忽略的 [env.sh](env.sh.example) 中。不要提交真实 API key。

常用配置：

| 变量 | 用途 |
| --- | --- |
| `RTC_EMBEDDING_API_KEY` | 真实语义代码搜索所需的 API key |
| `RTC_EMBEDDING_BASE_URL` | OpenAI 兼容 embedding endpoint |
| `RTC_EMBEDDING_MODEL` | Embedding 模型名 |
| `PY_BIN` | 可选的插件/后端 Python 覆盖 |
| `RTC_FILTER_ENABLED` | read/exec 过滤开关，默认 `1` |
| `RTC_INJECT_FILTERING_PROMPT` | 是否注入过滤策略说明 |

`requirements.txt` 已包含 `httpx[socks]`；`setup_env.sh` 也会为
`127.0.0.1`、`localhost` 和 `::1` 设置 `NO_PROXY`/`no_proxy`，避免本地
RTC/AGFS 请求走 HTTP(S)/SOCKS 代理。

## 重要文件

- [bootstrap.sh](bootstrap.sh)：一行命令完成本地准备。
- [env.sh.example](env.sh.example)：本地环境配置模板。
- [setup_env.sh](setup_env.sh)：共用环境加载脚本。
- [claude-plugin/prompts/code_policy_injection.txt](claude-plugin/prompts/code_policy_injection.txt)：Claude 策略 prompt。
- [openclaw-plugin/prompts/code_policy_injection.txt](openclaw-plugin/prompts/code_policy_injection.txt)：OpenClaw 策略 prompt。
- [docs/assets/readme/](docs/assets/readme/)：README 图表。用 `python3 docs/assets/readme/generate_readme_diagrams.py` 重新生成。
- [scripts/SWE/](scripts/SWE/)：SWE Lite runner 和报告。
- [LICENSE](LICENSE)：木兰宽松许可证第 2 版（`MulanPSL-2.0`）。

## SWE Lite Runner

SWE runner 会生成任务提示词，并以非交互方式启动 Claude 或 OpenClaw。

```bash
# Claude legacy
source scripts/SWE/claude/legacy/setup_swe_env.sh
./scripts/SWE/claude/legacy/run_swe_task_lite_plain_claude.sh

# Claude RTC/plugin
source scripts/SWE/claude/RTC/setup_swe_env.sh
./scripts/SWE/claude/RTC/run_swe_task_lite_rtc_plugin.sh

# OpenClaw legacy
source scripts/SWE/openclaw/legacy/setup_swe_env.sh
./scripts/SWE/openclaw/legacy/run_swe_task_lite_plain_openclaw.sh

# OpenClaw RTC/plugin
source scripts/SWE/openclaw/RTC/setup_swe_env.sh
./scripts/SWE/openclaw/RTC/run_swe_task_lite_openclaw_rtc_plugin.sh
```

默认情况下，`scripts/SWE/claude/RTC/setup_swe_env.sh` 会设置
`SWE_VALIDATION_FORCE_LOCAL=1`。验证会在任务专用的本地 SWE-bench 环境中运行，而不是官方 Docker harness。

生成数据不会进入 git。RTC 运行输出位于
`scripts/SWE/claude/RTC/output_logs/`；可复用的仓库 clone 缓存在项目外的
`${XDG_CACHE_HOME:-~/.cache}/retrieval-token-cutter/swe/rtc/cache/repo`。

## 许可证

本项目使用木兰宽松许可证第 2 版（`MulanPSL-2.0`）。详见 [LICENSE](LICENSE)。
