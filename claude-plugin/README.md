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

From a fresh clone, install the repository Python dependencies and create the
ignored local environment file:

```bash
cd /path/to/retrieval-token-cutter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp env.sh.example env.sh
$EDITOR env.sh
```

At minimum, set `RTC_EMBEDDING_API_KEY` for real code search. If you do not use
the repository `.venv`, set `PY_BIN` to a Python that can import `flask`,
`mcp`, `openai`, and `pyagfs`. The MCP launcher also checks common local Conda
paths such as `~/miniconda3/bin/python`.

If `agfs-server` is not on `PATH`, build the bundled AGFS server once:

```bash
(cd agfs && make build)
```

The plugin wrapper [setup_env.sh](setup_env.sh) simply sources
[../setup_env.sh](../setup_env.sh), which in turn sources the ignored `env.sh`.

## Start Claude

Recommended command when your values are in `env.sh`:

```bash
cd /path/to/project
/path/to/retrieval-token-cutter/claude-plugin/bin/rtc-claude
```

That helper sources the repository environment and then runs:

```bash
claude --plugin-dir /path/to/retrieval-token-cutter/claude-plugin
```

If your shell already exports the same environment values, you can run Claude
directly from the project Claude should edit:

```bash
cd /path/to/project
claude --plugin-dir /path/to/retrieval-token-cutter/claude-plugin
```

Do not pass `--mcp-config`; this plugin owns its `.mcp.json`.

The plugin MCP entrypoint and hook/manual commands honor `PY_BIN`. Without
`PY_BIN`, they try the repository `.venv`, common local Conda locations, and
then `python3`/`python` on `PATH`.

## Validate

Inside Claude:

```text
/plugin
```

Expected status:

```text
retrieval-token-cutter Plugin · inline · ✔ enabled
└ retrieval-token-cutter MCP · ✔ connected
```

Then try a code task:

```text
Fix the bug in the add function
```

The `UserPromptSubmit` hook injects the rendered [prompts/code_policy_injection.txt](prompts/code_policy_injection.txt). Claude should call:

```text
mcp__plugin_retrieval-token-cutter_retrieval-token-cutter__search_code
mcp__plugin_retrieval-token-cutter_retrieval-token-cutter__edit_file
```

If the status says environment variables such as `RTC_DIR` or
`RTC_RUNTIME_DIR` are missing, restart Claude with `claude-plugin/bin/rtc-claude`
from this checkout. Do not add a separate `--mcp-config`; the plugin's own
`.mcp.json` is the supported path.

The filtering-strategy section is controlled by `RTC_INJECT_FILTERING_PROMPT`.
Set it to `1` to include that section in interactive Claude sessions:

```bash
RTC_INJECT_FILTERING_PROMPT=1 claude-plugin/bin/rtc-render-code-policy
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
- `RTC_PLUGIN_HOOK_START_WAIT=8`: maximum normal wait, in seconds, for a cold hook to start RTC.
- `RTC_URL`: local Retrieval Token Cutter HTTP endpoint, default `http://127.0.0.1:8090`.
- `AGFS_BASE_URL`: local AGFS endpoint, default `http://127.0.0.1:1833`.
