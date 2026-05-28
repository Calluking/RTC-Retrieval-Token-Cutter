# 项目上下文

本仓库是一个精简版 Retrieval Token Cutter 运行时，包含 Claude Code 插件和 SWE Lite 运行器。

重要路径：

- `claude-plugin/`：可挂载的本地 Claude Code 插件。使用 `claude --plugin-dir ./claude-plugin` 加载。
- `claude-plugin/.mcp.json`：插件自带的 `retrieval-token-cutter` MCP 服务配置。
- `claude-plugin/retrieval_token_cutter_mcp/`：插件内置的 MCP 桥接层。
- `scripts/SWE/claude/RTC/run_swe_task_lite_rtc_plugin.sh`：使用 RTC 插件的 SWE Lite 运行器。
- `scripts/SWE/claude/RTC/README.md`：RTC 运行器使用说明。
- `code-version/`：SWE 运行器使用的运行时覆盖层。

不要提交生成目录：

- `.venv/`
- `scripts/SWE/claude/RTC/.cache/`
- `scripts/SWE/claude/RTC/output_logs/`
- `scripts/SWE/claude/legacy/.cache/`
- `scripts/SWE/claude/legacy/output_logs/`

密钥必须来自环境变量或已忽略的本地 `env.sh`，不要写入会提交的文件。
