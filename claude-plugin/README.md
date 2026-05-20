# Retrieval Token Cutter Claude Code Plugin

Local Claude Code plugin for Retrieval Token Cutter code search and MCP-based edits.

[中文文档](README_CN.md)

## What Gets Loaded

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

Claude loads this plugin with `--plugin-dir`. The plugin starts the bundled MCP server. The MCP server starts the local Retrieval Token Cutter backend and AGFS on demand.

## Configure

Copy the repository-level [../env.sh.example](../env.sh.example) to `../env.sh`, then fill in your local values. The plugin wrapper [setup_env.sh](setup_env.sh) simply sources [../setup_env.sh](../setup_env.sh).

Required values:

```bash
cd ..
cp env.sh.example env.sh
export RTC_EMBEDDING_API_KEY="<your-key>"
export RTC_EMBEDDING_BASE_URL="https://api.openai-proxy.org"
export RTC_EMBEDDING_MODEL="text-embedding-3-large"
```

If your shell uses an HTTP(S) or SOCKS proxy, source the top-level `setup_env.sh`
before launching Claude. It keeps `127.0.0.1`, `localhost`, and `::1` in
`NO_PROXY`/`no_proxy`, which is required because the plugin talks to local RTC
and AGFS services.

## Start Claude

From the project Claude should edit:

```bash
cd /path/to/project
source /path/to/retrieval-token-cutter/setup_env.sh
claude --plugin-dir "$RTC_CLAUDE_PLUGIN_DIR"
```

Do not pass `--mcp-config`; this plugin owns its `.mcp.json`.
The plugin MCP entrypoint and hook/manual commands honor `PY_BIN`, so the
virtual environment selected by `setup_env.sh` is the interpreter used inside
Claude as well.

## Validate

Inside Claude:

```text
/plugin
```

Then try a code task:

```text
Fix the bug in the add function
```

The `UserPromptSubmit` hook injects [prompts/code_policy_injection.txt](prompts/code_policy_injection.txt). Claude should call:

```text
mcp__plugin_retrieval-token-cutter_retrieval-token-cutter__search_code
mcp__plugin_retrieval-token-cutter_retrieval-token-cutter__edit_file
```

## Manual Commands

From the repository root:

```bash
claude-plugin/bin/rtc-status
claude-plugin/bin/rtc-start
claude-plugin/bin/rtc-stop
```

Memory helpers:

```bash
claude-plugin/bin/rtc-compose "what did we decide about MCP search?"
claude-plugin/bin/rtc-add-history --dry-run
claude-plugin/bin/rtc-add-history --yes
```

## Lifecycle

- `RTC_PLUGIN_AUTO_START=1`: auto-start backend services when needed.
- `RTC_PLUGIN_AUTO_STOP=1`: stop Retrieval Token Cutter and AGFS when Claude exits.
- `RTC_URL`: local Retrieval Token Cutter HTTP endpoint, default `http://127.0.0.1:8090`.
- `AGFS_BASE_URL`: local AGFS endpoint, default `http://127.0.0.1:1833`.
