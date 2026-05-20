# Project Context

This repository is a slim Retrieval Token Cutter runtime plus a Claude Code plugin and SWE Lite runner.

Important paths:

- `claude-plugin/`: attachable local Claude Code plugin. Load with `claude --plugin-dir ./claude-plugin`.
- `claude-plugin/.mcp.json`: plugin-owned MCP server config for `retrieval-token-cutter`.
- `claude-plugin/retrieval_token_cutter_mcp/`: bundled MCP bridge used by the plugin.
- `scripts/SWE/claude/RTC/run_swe_task_lite_rtc_plugin.sh`: RTC plugin SWE Lite runner.
- `scripts/SWE/claude/RTC/README.md`: RTC runner usage notes.
- `code-version/`: runtime overlay used by the SWE runner.

Do not commit generated directories:

- `.venv/`
- `scripts/SWE/claude/RTC/.cache/`
- `scripts/SWE/claude/RTC/output_logs/`
- `scripts/SWE/claude/legacy/.cache/`
- `scripts/SWE/claude/legacy/output_logs/`

Secrets must come from environment variables or ignored local `env.sh`, never committed files.
