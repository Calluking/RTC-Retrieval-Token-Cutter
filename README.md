# Retrieval Token Cutter

Make a local codebase searchable from Claude Code or OpenClaw with Retrieval Token Cutter semantic code search and exact-replacement file edits.

[中文文档](README_CN.md)

## What It Does

- Loads a `retrieval-token-cutter` Claude Code plugin from `claude-plugin/`.
- Loads a native OpenClaw plugin from `openclaw-plugin/`.
- Starts the local MCP bridge, AGFS, and Retrieval Token Cutter backend when Claude needs them.
- Starts the local AGFS and Retrieval Token Cutter backend when OpenClaw loads the plugin.
- Injects a code-search/edit policy before code-looking prompts.
- Exposes search and edit tools for code search and exact file edits.
- Stops services started by the plugin when the host exits.

## Requirements

- Python 3.11+
- Claude Code CLI, OpenClaw CLI, or both, already installed and logged in
- `agfs-server`, either on `PATH` or built at `agfs/build/agfs-server`
- Go 1.21+, if you build the bundled AGFS server from this repository
- An OpenAI-compatible embedding endpoint and API key
- Conda, if you use the SWE runner's default task-specific local validation environment
- `requirements.txt` includes `httpx[socks]` so SOCKS proxy URLs work with OpenAI-compatible clients. `setup_env.sh` also exports `NO_PROXY`/`no_proxy` for `127.0.0.1`, `localhost`, and `::1` so local RTC/AGFS calls bypass HTTP(S)/SOCKS proxies.

Install Python dependencies:

```bash
cd /path/to/retrieval-token-cutter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If `agfs-server` is not already on `PATH`, build the bundled server:

```bash
(cd agfs && make build)
```

If you use `uv`, install the plugin and SWE runner extras:

```bash
uv sync --extra mcp --extra swe
```

## Configure

Create local `env.sh` from [env.sh.example](env.sh.example), then edit it with
your local values:

```bash
cp env.sh.example env.sh
$EDITOR env.sh
```

At minimum, set `RTC_EMBEDDING_API_KEY` for real code search. If you do not use
the repository `.venv`, set `PY_BIN` to a Python that can import `flask`,
`mcp`, `openai`, and `pyagfs`. The Claude plugin launcher also checks common
local Conda paths such as `~/miniconda3/bin/python`.

Do not commit real API keys.

## Fresh Clone Quickstart

From a new checkout, prepare the repository once:

```bash
cd /path/to/retrieval-token-cutter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp env.sh.example env.sh
$EDITOR env.sh
```

Set at least `RTC_EMBEDDING_API_KEY` in `env.sh`. If `agfs-server` is not on
`PATH`, also build the bundled server:

```bash
(cd agfs && make build)
```

After that, Claude and OpenClaw use different launch steps.

## Start Claude

Best default when you keep local values in `env.sh`:

```bash
cd /path/to/project
/path/to/retrieval-token-cutter/claude-plugin/bin/rtc-claude
```

That helper sources `env.sh`, then runs Claude with this plugin directory.

If your shell already exports the RTC environment variables, the direct Claude
command is also fine:

From the project you want Claude to edit, run exactly:

```bash
cd /path/to/project
claude --plugin-dir /path/to/retrieval-token-cutter/claude-plugin
```

Do not pass `--mcp-config`; the plugin owns its `.mcp.json`. The plugin starts
its MCP server immediately and starts the RTC/AGFS backend on demand.

Then ask Claude something like:

```text
Fix the bug in the add function
```

For code-looking prompts, the plugin injects the MCP workflow policy automatically.

## Start OpenClaw

Install the linked OpenClaw plugin once from this repository:

```bash
cd /path/to/retrieval-token-cutter
openclaw plugins install --link ./openclaw-plugin --dangerously-force-unsafe-install
openclaw plugins enable retrieval-token-cutter
openclaw gateway restart
```

If you previously installed the plugin from another checkout, uninstall the old
registration first so OpenClaw relinks this clone:

```bash
openclaw plugins uninstall retrieval-token-cutter --force
openclaw plugins install --link ./openclaw-plugin --dangerously-force-unsafe-install
```

OpenClaw requires `--dangerously-force-unsafe-install` because this plugin auto-starts local RTC/AGFS processes through Node's child process API.

On a fresh clone, no `source setup_env.sh`, `RTC_DIR`, `RTC_RUNTIME_DIR`, or
`RTC_WORKSPACE_ROOT` is needed for interactive OpenClaw. The linked plugin
discovers this repository, imports `env.sh` through `setup_env.sh`, starts
RTC/AGFS, and uses the directory where you start OpenClaw as the workspace.

From the project you want OpenClaw to edit, start the local TUI:

```bash
cd /path/to/project
openclaw chat --local
```

The linked plugin discovers this repository from `./openclaw-plugin`, imports
`setup_env.sh` automatically, uses the current directory as the workspace, and
enables RTC read/exec filtering by default. `openclaw chat` is the official
local embedded TUI entrypoint. It is equivalent to `openclaw tui --local`.
Use `--session "rtc-$(date +%s)"` only when you intentionally want an isolated
throwaway chat history.

Then ask:

```text
Fix the bug in the add function.
```

## Verify

Inside Claude:

```text
/plugin
```

You should see:

```text
retrieval-token-cutter Plugin · inline · ✔ enabled
└ retrieval-token-cutter MCP · ✔ connected
```

In Claude Code debug logs, successful code work should include calls like:

```text
mcp__plugin_retrieval-token-cutter_retrieval-token-cutter__search_code
mcp__plugin_retrieval-token-cutter_retrieval-token-cutter__edit_file
```

For OpenClaw, verify the plugin is loaded:

```bash
openclaw plugins inspect retrieval-token-cutter --runtime --json
```

The runtime output should include:

```text
rtc_health
rtc_index_codebase
rtc_search_code
rtc_edit_file
```

To confirm a run used search, inspect the latest session log:

```bash
latest=$(ls -t ~/.openclaw/agents/*/sessions/*.jsonl | grep -v trajectory | head -1)
rg -n "Retrieval Token Cutter|FILTER IS TRIGGERED|rtc_search_code|rtc_edit_file" "$latest"
```

For Claude, inspect the current Claude debug log or the `/plugin` panel. A
healthy run should show the plugin connected and MCP tool names containing
`search_code` and `edit_file`.

## Useful Files

- [env.sh.example](env.sh.example): local environment configuration template. Copy it to ignored `env.sh`.
- [setup_env.sh](setup_env.sh): shared environment loader used by the plugin launchers.
- [claude-plugin/](claude-plugin/): local Claude Code plugin.
- [openclaw-plugin/](openclaw-plugin/): native OpenClaw plugin.
- [claude-plugin/prompts/code_policy_injection.txt](claude-plugin/prompts/code_policy_injection.txt): injected MCP coding policy.
- [openclaw-plugin/prompts/code_policy_injection.txt](openclaw-plugin/prompts/code_policy_injection.txt): injected OpenClaw coding policy.
- [scripts/SWE/claude/RTC/](scripts/SWE/claude/RTC/): Retrieval Token Cutter plugin-based SWE Lite runner.
- [scripts/SWE/claude/legacy/](scripts/SWE/claude/legacy/): plain Claude SWE Lite runner without the plugin.
- [scripts/SWE/openclaw/RTC/](scripts/SWE/openclaw/RTC/): Retrieval Token Cutter OpenClaw plugin-based SWE Lite runner.
- [scripts/SWE/openclaw/legacy/](scripts/SWE/openclaw/legacy/): plain OpenClaw SWE Lite runner without the plugin.

## SWE Lite Runner

The SWE runners build a task prompt and start Claude or OpenClaw non-interactively.

Claude legacy:

```bash
source scripts/SWE/claude/legacy/setup_swe_env.sh
./scripts/SWE/claude/legacy/run_swe_task_lite_plain_claude.sh
```

Claude RTC/plugin:

```bash
source scripts/SWE/claude/RTC/setup_swe_env.sh
./scripts/SWE/claude/RTC/run_swe_task_lite_rtc_plugin.sh
```

OpenClaw legacy:

```bash
source scripts/SWE/openclaw/legacy/setup_swe_env.sh
./scripts/SWE/openclaw/legacy/run_swe_task_lite_plain_openclaw.sh
```

OpenClaw RTC/plugin:

```bash
source scripts/SWE/openclaw/RTC/setup_swe_env.sh
./scripts/SWE/openclaw/RTC/run_swe_task_lite_openclaw_rtc_plugin.sh
```

See [scripts/SWE/claude/RTC/README.md](scripts/SWE/claude/RTC/README.md), [scripts/SWE/claude/legacy/README.md](scripts/SWE/claude/legacy/README.md), [scripts/SWE/openclaw/RTC/README.md](scripts/SWE/openclaw/RTC/README.md), and [scripts/SWE/openclaw/legacy/README.md](scripts/SWE/openclaw/legacy/README.md).

By default, `scripts/SWE/claude/RTC/setup_swe_env.sh` sets `SWE_VALIDATION_FORCE_LOCAL=1`. Validation then runs in the local task-specific SWE-bench environment instead of the official Docker harness, which avoids Docker network problems on machines where containers cannot reach GitHub. This local path derives commands from the SWE-bench `TestSpec` and applies the benchmark test patch, but the official Docker harness is still the stricter final behavior. Set `SWE_VALIDATION_FORCE_LOCAL=0` to try the official Docker harness.

## Notes

Generated data is ignored by git. The RTC SWE runner keeps analyzable run output under `scripts/SWE/claude/RTC/output_logs/`, including AGFS data and rendered transcripts, while reusable repository clones live outside the project under `${XDG_CACHE_HOME:-~/.cache}/retrieval-token-cutter/swe/rtc/cache/repo`. After validation, generated workspace Git metadata is moved aside so editors do not show every SWE run as a nested repository.
