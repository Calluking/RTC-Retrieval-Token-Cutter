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

先把仓库根目录的 [../env.sh.example](../env.sh.example) 复制为 `../env.sh`，再填写本地配置。插件目录里的 [setup_env.sh](setup_env.sh) 只是转发到 [../setup_env.sh](../setup_env.sh)。

需要填写：

```bash
cd ..
cp env.sh.example env.sh
export RTC_EMBEDDING_API_KEY="<your-key>"
export RTC_EMBEDDING_BASE_URL="https://api.openai-proxy.org"
export RTC_EMBEDDING_MODEL="text-embedding-3-small"
```

如果 shell 使用 HTTP(S) 或 SOCKS 代理，请在启动 Claude 前 source 顶层
`setup_env.sh`。它会把 `127.0.0.1`、`localhost` 和 `::1` 放进
`NO_PROXY`/`no_proxy`，因为插件需要直连本地 RTC 和 AGFS 服务。

## 启动 Claude

在 Claude 要修改的项目目录里运行：

```bash
cd /path/to/project
source /path/to/retrieval-token-cutter/setup_env.sh
claude --plugin-dir "$RTC_CLAUDE_PLUGIN_DIR"
```

不要传 `--mcp-config`，插件自带 `.mcp.json`。
插件 MCP 入口、hooks 和手动命令都会尊重 `PY_BIN`，因此 `setup_env.sh`
选中的虚拟环境也会被 Claude 内部使用。

## 验证

在 Claude 里运行：

```text
/plugin
```

然后尝试一个代码任务：

```text
Fix the bug in the add function
```

`UserPromptSubmit` hook 会注入 [prompts/code_policy_injection.txt](prompts/code_policy_injection.txt)。Claude 应该调用：

```text
mcp__plugin_retrieval-token-cutter_retrieval-token-cutter__search_code
mcp__plugin_retrieval-token-cutter_retrieval-token-cutter__edit_file
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
- `RTC_URL`：本地 Retrieval Token Cutter HTTP endpoint，默认 `http://127.0.0.1:8090`。
- `AGFS_BASE_URL`：本地 AGFS endpoint，默认 `http://127.0.0.1:1833`。
