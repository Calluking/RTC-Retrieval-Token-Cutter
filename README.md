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
- Claude Code CLI, OpenClaw CLI, or both
- `agfs-server`, either on `PATH` or built at `agfs/build/agfs-server`
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

If you use `uv`, install the plugin and SWE runner extras:

```bash
uv sync --extra mcp --extra swe
```

## Configure

Create local `env.sh` from [env.sh.example](env.sh.example) before running Claude:

```bash
cp env.sh.example env.sh
export RTC_EMBEDDING_API_KEY="<your-key>"
export RTC_EMBEDDING_BASE_URL="https://api.openai.com"
export RTC_EMBEDDING_MODEL="text-embedding-3-large"
```

If you use the virtual environment above, you can leave `PY_BIN` empty. `setup_env.sh` will detect `.venv/bin/python`.

Do not commit real API keys.

## Start Claude

From the project you want Claude to edit, run exactly:

```bash
cd /path/to/project
source /path/to/retrieval-token-cutter/setup_env.sh
claude --plugin-dir "$RTC_CLAUDE_PLUGIN_DIR"
```

Then ask Claude something like:

```text
Fix the bug in the add function
```

For code-looking prompts, the plugin injects the MCP workflow policy automatically.

## Start OpenClaw

Install the linked OpenClaw plugin once from this repository:

```bash
cd /path/to/retrieval-token-cutter
source setup_env.sh
openclaw plugins install --link ./openclaw-plugin --dangerously-force-unsafe-install
openclaw plugins enable retrieval-token-cutter
openclaw gateway restart
```

OpenClaw requires `--dangerously-force-unsafe-install` because this plugin auto-starts local RTC/AGFS processes through Node's child process API.

From the project you want OpenClaw to edit, start a fresh local TUI session:

```bash
cd /path/to/project
source /path/to/retrieval-token-cutter/setup_env.sh
export RTC_WORKSPACE_ROOT="$PWD"
openclaw chat --local --session "rtc-$(date +%s)"
```

`openclaw chat` is the official local embedded TUI entrypoint. It is equivalent to `openclaw tui --local`. Passing a fresh `--session` avoids reusing the default `agent:<agent>:main` history.

Then ask:

```text
Fix the bug in the add function.
```

## Verify

Inside Claude:

```text
/plugin
```

You should see `retrieval-token-cutter` with no loading errors.

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
rg -n "rtc_search_code|rtc_edit_file|python -m pytest|Fix the bug" "$latest"
```

## Useful Files

- [env.sh.example](env.sh.example): local environment configuration template. Copy it to ignored `env.sh`.
- [setup_env.sh](setup_env.sh): one-line setup script used before starting Claude.
- [claude-plugin/](claude-plugin/): local Claude Code plugin.
- [openclaw-plugin/](openclaw-plugin/): native OpenClaw plugin.
- [claude-plugin/prompts/code_policy_injection.txt](claude-plugin/prompts/code_policy_injection.txt): injected MCP coding policy.
- [openclaw-plugin/prompts/code_policy_injection.txt](openclaw-plugin/prompts/code_policy_injection.txt): injected OpenClaw coding policy.
- [scripts/SWE/claude/RTC/](scripts/SWE/claude/RTC/): Retrieval Token Cutter plugin-based SWE Lite runner.
- [scripts/SWE/claude/legacy/](scripts/SWE/claude/legacy/): plain Claude SWE Lite runner without the plugin.

## SWE Lite Runner

The SWE runner builds a task prompt and starts Claude in print mode:

```bash
source scripts/SWE/claude/RTC/setup_swe_env.sh
./scripts/SWE/claude/RTC/run_swe_task_lite_rtc_plugin.sh
```

See [scripts/SWE/claude/RTC/README.md](scripts/SWE/claude/RTC/README.md) and [scripts/SWE/claude/legacy/README.md](scripts/SWE/claude/legacy/README.md).

By default, `scripts/SWE/claude/RTC/setup_swe_env.sh` sets `SWE_VALIDATION_FORCE_LOCAL=1`. Validation then runs in the local task-specific SWE-bench environment instead of the official Docker harness, which avoids Docker network problems on machines where containers cannot reach GitHub. This local path derives commands from the SWE-bench `TestSpec` and applies the benchmark test patch, but the official Docker harness is still the stricter final behavior. Set `SWE_VALIDATION_FORCE_LOCAL=0` to try the official Docker harness.

## Notes

Generated data is ignored by git. The RTC SWE runner keeps analyzable run output under `scripts/SWE/claude/RTC/output_logs/`, including AGFS data and rendered transcripts, while reusable repository clones live outside the project under `${XDG_CACHE_HOME:-~/.cache}/retrieval-token-cutter/swe/rtc/cache/repo`. After validation, generated workspace Git metadata is moved aside so editors do not show every SWE run as a nested repository.
