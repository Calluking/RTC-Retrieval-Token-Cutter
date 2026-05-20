# Retrieval Token Cutter for OpenClaw

Native OpenClaw plugin for Retrieval Token Cutter code search and exact string replacement edits.

The plugin exposes these OpenClaw tools:

- `rtc_search_code`
- `rtc_edit_file`
- `rtc_index_codebase`
- `rtc_health`

It can also start the local RTC and AGFS services when OpenClaw loads the plugin, then stop the services it started when OpenClaw exits.

For code-looking prompts, the plugin injects a policy that asks the agent to call `rtc_search_code` before broad file reads and to use `rtc_edit_file` for the patch when practical.

## Install

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Keep secret embedding settings in your shell environment, for example in `~/.bashrc`:

```bash
export RTC_EMBEDDING_API_KEY="<your-key>"
export RTC_EMBEDDING_BASE_URL="https://api.openai-proxy.org"
export RTC_EMBEDDING_MODEL="text-embedding-3-large"
```

Then install the plugin as a linked local plugin:

```bash
cd /path/to/retrieval-token-cutter
source setup_env.sh
openclaw plugins install --link ./openclaw-plugin --dangerously-force-unsafe-install
openclaw plugins enable retrieval-token-cutter
openclaw gateway restart
```

If this plugin was already installed from another checkout, uninstall the old
registration first and relink the current clone:

```bash
openclaw plugins uninstall retrieval-token-cutter --force
openclaw plugins install --link ./openclaw-plugin --dangerously-force-unsafe-install
```

OpenClaw asks for the explicit unsafe-install flag because this plugin starts
local RTC/AGFS processes through Node's child process API. That is expected for
auto-start. The plugin starts only local services from this repository.

Verify it:

```bash
openclaw plugins inspect retrieval-token-cutter --runtime --json
```

The runtime output should show `status: "loaded"`, the service `retrieval-token-cutter`, and these tools:

```text
rtc_health
rtc_index_codebase
rtc_search_code
rtc_edit_file
```

## Configure

The plugin works with environment variables from `setup_env.sh` and `env.sh`.

Useful optional config keys under `plugins.entries.retrieval-token-cutter.config`:

```json
{
  "workspaceRoot": "/path/to/project",
  "rtcUrl": "http://127.0.0.1:8090",
  "autoStart": true,
  "autoStop": true,
  "injectCodePolicy": true
}
```

If `workspaceRoot` is omitted, the plugin uses `RTC_WORKSPACE_ROOT`, then OpenClaw's process working directory.

## Start OpenClaw

OpenClaw's official local embedded TUI command is:

```bash
openclaw chat
```

It is equivalent to:

```bash
openclaw tui --local
```

For RTC work, start it from the target project and pass a fresh session name so OpenClaw does not reuse `agent:<agent>:main` history:

```bash
cd /path/to/project
source /path/to/retrieval-token-cutter/setup_env.sh
export RTC_WORKSPACE_ROOT="$PWD"
openclaw chat --local --session "rtc-$(date +%s)"
```

Then ask normally:

```text
Fix the bug in the add function.
```

The TUI may keep tool cards collapsed. Absence of visible `rtc_search_code` text in the terminal does not mean search was skipped.

## Verify A Run Used Search

Find the newest OpenClaw session JSONL and search for RTC tool calls:

```bash
latest=$(ls -t ~/.openclaw/agents/*/sessions/*.jsonl | grep -v trajectory | head -1)
rg -n "rtc_search_code|rtc_edit_file|python -m pytest|Fix the bug" "$latest"
```

A successful run should include a flow like:

```text
TOOL CALL: rtc_search_code
TOOL RESULT: rtc_search_code
TOOL CALL: rtc_edit_file
TOOL RESULT: rtc_edit_file
TOOL CALL: exec
```

Example `rtc_search_code` arguments:

```json
{
  "path": "/path/to/project",
  "query": "add function"
}
```

## Runtime

Default runtime directory:

```text
~/.cache/retrieval-token-cutter-openclaw-plugin
```

Manual service commands are still available through the shared RTC terminal script:

```bash
source setup_env.sh
"$PY_BIN" claude-plugin/scripts/rtc_terminal.py start --runtime-dir ~/.cache/retrieval-token-cutter-openclaw-plugin
"$PY_BIN" claude-plugin/scripts/rtc_terminal.py status --runtime-dir ~/.cache/retrieval-token-cutter-openclaw-plugin
"$PY_BIN" claude-plugin/scripts/rtc_terminal.py stop --runtime-dir ~/.cache/retrieval-token-cutter-openclaw-plugin
```
