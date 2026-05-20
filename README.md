# Retrieval Token Cutter Claude Plugin

Make a local codebase searchable from Claude Code with Retrieval Token Cutter semantic code search, MCP tools, and an attachable Claude plugin.

[中文文档](README_CN.md)

## What It Does

- Loads a `retrieval-token-cutter` Claude Code plugin from `claude-plugin/`.
- Starts the local MCP bridge, AGFS, and Retrieval Token Cutter backend when Claude needs them.
- Injects the code-search/edit policy from `claude-plugin/prompts/code_policy_injection.txt`.
- Exposes MCP tools for code search and MCP-based file edits.
- Stops the Retrieval Token Cutter and AGFS services when Claude exits.

## Requirements

- Python 3.11+
- Claude Code CLI
- `agfs-server`, either on `PATH` or built at `agfs/build/agfs-server`
- An OpenAI-compatible embedding endpoint and API key
- Conda, if you use the SWE runner's default task-specific local validation environment
- `requirements.txt` includes `httpx[socks]` so SOCKS proxy URLs work with OpenAI-compatible clients. `setup_env.sh` also exports `NO_PROXY`/`no_proxy` for `127.0.0.1`, `localhost`, and `::1` so local RTC/AGFS calls bypass HTTP(S)/SOCKS proxies.

Install Python dependencies:

```bash
cd /path/to/retrieval-token-cutter-claude-plugin
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
source /path/to/retrieval-token-cutter-claude-plugin/setup_env.sh
claude --plugin-dir "$RTC_CLAUDE_PLUGIN_DIR"
```

Then ask Claude something like:

```text
Fix the bug in the add function
```

For code-looking prompts, the plugin injects the MCP workflow policy automatically.

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

## Useful Files

- [env.sh.example](env.sh.example): local environment configuration template. Copy it to ignored `env.sh`.
- [setup_env.sh](setup_env.sh): one-line setup script used before starting Claude.
- [claude-plugin/](claude-plugin/): local Claude Code plugin.
- [claude-plugin/prompts/code_policy_injection.txt](claude-plugin/prompts/code_policy_injection.txt): injected MCP coding policy.
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
