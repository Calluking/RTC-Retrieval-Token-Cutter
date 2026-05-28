# Retrieval Token Cutter Claude Code 插件

用于 Retrieval Token Cutter 代码搜索和 MCP 文件编辑的本地 Claude Code 插件。

[English README](README.md)

## Claude 会加载什么

```text
claude-plugin/
|-- .claude-plugin/plugin.json
|-- .mcp.json
|-- hooks/hooks.json
|-- prompts/code_policy_injection.txt
|-- skills/
|-- bin/
|-- scripts/
`-- retrieval_token_cutter_mcp/
```

Claude 通过 `--plugin-dir` 加载这个插件。插件会启动内置 MCP server，MCP server 会按需启动本地 Retrieval Token Cutter 后端和 AGFS。

## 配置

先把仓库根目录的 [../env.sh.example](../env.sh.example) 复制为 `../env.sh`，
然后编辑里面的本地配置。插件目录里的 [setup_env.sh](setup_env.sh) 只是转发到
[../setup_env.sh](../setup_env.sh)。

需要填写：

```bash
cd ..
cp env.sh.example env.sh
$EDITOR env.sh
```

实际做代码搜索时，至少要设置 `RTC_EMBEDDING_API_KEY`。如果不使用仓库里的
`.venv`，请把 `PY_BIN` 指向能 import `flask`、`mcp`、`openai` 和
`pyagfs` 的 Python。MCP 启动器也会检查常见本地 Conda 路径，例如
`~/miniconda3/bin/python`。

## 启动 Claude

在 Claude 要修改的项目目录里运行：

```bash
cd /path/to/project
claude --plugin-dir /path/to/retrieval-token-cutter/claude-plugin
```

不要传 `--mcp-config`，插件自带 `.mcp.json`。

如果环境变量只写在被 git 忽略的 `env.sh` 里，请使用 helper 启动器，
这样启动 Claude 前会先 source 它：

```bash
cd /path/to/project
/path/to/retrieval-token-cutter/claude-plugin/bin/rtc-claude
```

插件 MCP 入口、hooks 和手动命令都会尊重 `PY_BIN`。如果没有设置 `PY_BIN`，
它们会依次尝试仓库 `.venv`、常见本地 Conda 路径，以及 `PATH` 上的
`python3`/`python`。

## 验证

在 Claude 里运行：

```text
/plugin
```

预期状态：

```text
retrieval-token-cutter Plugin · inline · ✔ enabled
└ retrieval-token-cutter MCP · ✔ connected
```

然后尝试一个代码任务：

```text
Fix the bug in the add function
```

`UserPromptSubmit` hook 会注入渲染后的 [prompts/code_policy_injection.txt](prompts/code_policy_injection.txt)。Claude 应该调用：

```text
mcp__plugin_retrieval-token-cutter_retrieval-token-cutter__search_code
mcp__plugin_retrieval-token-cutter_retrieval-token-cutter__edit_file
```

过滤策略说明由 `RTC_INJECT_FILTERING_PROMPT` 控制。设为 `1` 时，交互式
Claude 会注入该段说明：

```bash
RTC_INJECT_FILTERING_PROMPT=1 claude-plugin/bin/rtc-render-code-policy
```

## 手动命令

在仓库根目录运行：

```bash
claude-plugin/bin/rtc-status
claude-plugin/bin/rtc-start
claude-plugin/bin/rtc-stop
```

记忆辅助命令：

```bash
claude-plugin/bin/rtc-compose "what did we decide about MCP search?"
claude-plugin/bin/rtc-add-history --dry-run
claude-plugin/bin/rtc-add-history --yes
```

## 生命周期

- `RTC_PLUGIN_AUTO_START=1`：需要时自动启动后端服务。
- `RTC_PLUGIN_AUTO_STOP=1`：Claude 退出时停止 Retrieval Token Cutter 和 AGFS。
- `RTC_PLUGIN_HOOK_START_WAIT=8`：冷启动 hook 等待 RTC 启动的常规上限，单位为秒。
- `RTC_URL`：本地 Retrieval Token Cutter HTTP endpoint，默认 `http://127.0.0.1:8090`。
- `AGFS_BASE_URL`：本地 AGFS endpoint，默认 `http://127.0.0.1:1833`。
