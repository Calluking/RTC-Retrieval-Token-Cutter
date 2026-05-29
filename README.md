<p align="center">
  <img src="docs/assets/readme/RTC/LOGO_BACKGROUND.png" alt="Retrieval Token Cutter" width="760">
</p>

# Retrieval Token Cutter

<p align="center">
  <a href="LICENSE"><img alt="License: MulanPSL-2.0" src="https://img.shields.io/badge/License-MulanPSL--2.0-2ea44f?style=for-the-badge"></a>
  <a href="pyproject.toml"><img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-3776ab?style=for-the-badge&logo=python&logoColor=white"></a>
  <a href="pyproject.toml"><img alt="Version 0.1.0" src="https://img.shields.io/badge/Version-0.1.0-0f766e?style=for-the-badge"></a>
  <a href="claude-plugin/"><img alt="Claude Code plugin" src="https://img.shields.io/badge/Claude%20Code-plugin-6b46c1?style=for-the-badge"></a>
  <a href="openclaw-plugin/"><img alt="OpenClaw plugin" src="https://img.shields.io/badge/OpenClaw-plugin-2563eb?style=for-the-badge"></a>
  <a href="filter/"><img alt="RTC filter enabled" src="https://img.shields.io/badge/RTC%20Filter-read%20%2B%20bash-f59e0b?style=for-the-badge"></a>
  <a href="agfs/"><img alt="AGFS local memory" src="https://img.shields.io/badge/AGFS-local%20memory-14b8a6?style=for-the-badge"></a>
</p>

Make a local codebase searchable from Claude Code or OpenClaw with semantic code
search, filtered long outputs, and exact-replacement file edits.

[中文文档](README_CN.md)

## Overview

Retrieval Token Cutter ships two local plugins:

| Host | Plugin | What it adds |
| --- | --- | --- |
| Claude Code | [claude-plugin/](claude-plugin/) | MCP tools for code search/edit plus prompt policy injection |
| OpenClaw | [openclaw-plugin/](openclaw-plugin/) | Native tools, prompt policy injection, and read/exec filtering |

Both plugins can start the local Retrieval Token Cutter backend and AGFS service
for you, then stop the services they started when the host exits.

![Runtime architecture](<docs/assets/readme/RTC/EN_Runtime Architecture.png>)

## Requirements

- Python 3.11+
- Go 1.21+
- Claude Code CLI, OpenClaw CLI, or both, already installed and logged in
- An OpenAI-compatible embedding endpoint and API key
- Conda, only if you use the SWE runner's default local validation environment

## Quickstart

Prepare a fresh checkout once:

```bash
cd /path/to/retrieval-token-cutter
./bootstrap.sh
$EDITOR env.sh
```

Set at least this value in `env.sh`:

```bash
export RTC_EMBEDDING_API_KEY="<your-key>"
```

`./bootstrap.sh` creates `.venv`, installs `requirements.txt`, creates `env.sh`
if missing, and builds `agfs/build/agfs-server`.

![Fresh clone quickstart](<docs/assets/readme/RTC/EN_Fresh Clone Start.png>)

Useful variants:

```bash
./bootstrap.sh --help
./bootstrap.sh --force-agfs
./bootstrap.sh --install-openclaw-plugin
```

If you prefer manual setup:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp env.sh.example env.sh
make -C agfs build
```

## Start Claude

From the project you want Claude to edit:

```bash
cd /path/to/project
/path/to/retrieval-token-cutter/claude-plugin/bin/rtc-claude
```

That helper loads `env.sh` and runs Claude with this plugin directory. If your
shell already exports the same RTC environment, the direct command is also fine:

```bash
cd /path/to/project
claude --plugin-dir /path/to/retrieval-token-cutter/claude-plugin
```

Do not pass `--mcp-config`; the Claude plugin owns its `.mcp.json`.

## Start OpenClaw

Install the linked OpenClaw plugin once:

```bash
cd /path/to/retrieval-token-cutter
./bootstrap.sh --install-openclaw-plugin
```

Equivalent manual commands:

```bash
openclaw plugins install --link ./openclaw-plugin --dangerously-force-unsafe-install
openclaw plugins enable retrieval-token-cutter
openclaw gateway restart
```

OpenClaw requires `--dangerously-force-unsafe-install` because this plugin
auto-starts local RTC/AGFS processes through Node's child process API.

Then start OpenClaw from the project you want to edit:

```bash
cd /path/to/project
openclaw chat --local
```

No `source setup_env.sh`, `RTC_DIR`, `RTC_RUNTIME_DIR`, or `RTC_WORKSPACE_ROOT`
is needed for normal interactive use. The linked plugin discovers this repo,
loads `env.sh`, starts RTC/AGFS, and uses the directory where you start
OpenClaw as the workspace.

## Verify

Claude:

```text
/plugin
```

Expected status:

```text
retrieval-token-cutter Plugin · inline · ✔ enabled
└ retrieval-token-cutter MCP · ✔ connected
```

OpenClaw:

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

To confirm a run used RTC search/filtering:

```bash
latest=$(ls -t ~/.openclaw/agents/*/sessions/*.jsonl | grep -v trajectory | head -1)
rg -n "Retrieval Token Cutter|FILTER IS TRIGGERED|rtc_search_code|rtc_edit_file" "$latest"
```

For Claude, inspect the current Claude debug log or the `/plugin` panel. A
healthy code run should show MCP tool names containing `search_code` and
`edit_file`.

![Code task flow](<docs/assets/readme/RTC/EN_Code Task Flow.png>)

## Configuration

Local settings live in ignored [env.sh](env.sh.example). Do not commit real API
keys.

Common settings:

| Variable | Purpose |
| --- | --- |
| `RTC_EMBEDDING_API_KEY` | API key for real semantic code search |
| `RTC_EMBEDDING_BASE_URL` | OpenAI-compatible embedding endpoint |
| `RTC_EMBEDDING_MODEL` | Embedding model name |
| `PY_BIN` | Optional Python override for plugin/backend runtime |
| `RTC_FILTER_ENABLED` | Toggle read/exec filtering, default `1` |
| `RTC_INJECT_FILTERING_PROMPT` | Toggle the filtering-strategy prompt section |

`requirements.txt` includes `httpx[socks]`, and `setup_env.sh` sets
`NO_PROXY`/`no_proxy` for `127.0.0.1`, `localhost`, and `::1` so local RTC/AGFS
traffic bypasses HTTP(S)/SOCKS proxies.

## Useful Files

- [bootstrap.sh](bootstrap.sh): one-command local setup.
- [env.sh.example](env.sh.example): local environment template.
- [setup_env.sh](setup_env.sh): shared environment loader.
- [claude-plugin/prompts/code_policy_injection.txt](claude-plugin/prompts/code_policy_injection.txt): Claude policy prompt.
- [openclaw-plugin/prompts/code_policy_injection.txt](openclaw-plugin/prompts/code_policy_injection.txt): OpenClaw policy prompt.
- [docs/assets/readme/](docs/assets/readme/): generated README diagrams. Refresh with `python3 docs/assets/readme/generate_readme_diagrams.py`.
- [scripts/SWE/](scripts/SWE/): SWE Lite runners and reports.
- [LICENSE](LICENSE): Mulan Permissive Software License v2 (`MulanPSL-2.0`).

## SWE Lite Runner

The SWE runners build a task prompt and start Claude or OpenClaw
non-interactively.

```bash
# Claude legacy
source scripts/SWE/claude/legacy/setup_swe_env.sh
./scripts/SWE/claude/legacy/run_swe_task_lite_plain_claude.sh

# Claude RTC/plugin
source scripts/SWE/claude/RTC/setup_swe_env.sh
./scripts/SWE/claude/RTC/run_swe_task_lite_rtc_plugin.sh

# OpenClaw legacy
source scripts/SWE/openclaw/legacy/setup_swe_env.sh
./scripts/SWE/openclaw/legacy/run_swe_task_lite_plain_openclaw.sh

# OpenClaw RTC/plugin
source scripts/SWE/openclaw/RTC/setup_swe_env.sh
./scripts/SWE/openclaw/RTC/run_swe_task_lite_openclaw_rtc_plugin.sh
```

By default, `scripts/SWE/claude/RTC/setup_swe_env.sh` sets
`SWE_VALIDATION_FORCE_LOCAL=1`. Validation then runs in the local
task-specific SWE-bench environment instead of the official Docker harness.

Generated SWE data is ignored by git. RTC run output goes under
`scripts/SWE/claude/RTC/output_logs/`; reusable repository clones live outside
the project under `${XDG_CACHE_HOME:-~/.cache}/retrieval-token-cutter/swe/rtc/cache/repo`.

## License

This project is licensed under the Mulan Permissive Software License v2
(`MulanPSL-2.0`). See [LICENSE](LICENSE).
