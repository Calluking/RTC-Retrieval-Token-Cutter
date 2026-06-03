<p align="center">
  <img src="docs/assets/readme/RTC/LOGO_BACKGROUND.png" alt="Retrieval Token Cutter" width="760">
</p>

# Retrieval Token Cutter

<p align="center">
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MulanPSL--2.0-blue.svg"></a>
  <a href="pyproject.toml"><img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-blue.svg"></a>
  <a href="pyproject.toml"><img alt="Version" src="https://img.shields.io/badge/version-0.1.0-blue.svg"></a>
  <a href="claude-plugin/"><img alt="Claude Code" src="https://img.shields.io/badge/Claude%20Code-plugin-purple.svg"></a>
  <a href="openclaw-plugin/"><img alt="OpenClaw" src="https://img.shields.io/badge/OpenClaw-plugin-blue.svg"></a>
  <a href="filter/"><img alt="RTC Filter" src="https://img.shields.io/badge/filter-read%20%2B%20bash-orange.svg"></a>
  <a href="agfs/"><img alt="AGFS" src="https://img.shields.io/badge/AGFS-local%20memory-teal.svg"></a>
</p>

Make a local codebase searchable from Claude Code or OpenClaw with semantic code
search, filtered long outputs, and exact-replacement file edits.

[中文文档](README_CN.md)

## Usage Cost Reduction

The SWE Lite verification reports include token and turn breakdowns for Claude
Code and OpenClaw runs. We chose `text-embedding-3-large` as the embedding
model.

| Claude Code | OpenClaw |
| --- | --- |
| ![Average usage cost, Claude Code](docs/assets/readme/average_usage_cost_barchart.png) | ![Average usage cost, OpenClaw](docs/assets/readme/average_usage_cost_barchart_openclaw.png) |

### Claude Average Per Task

| Metric | Legacy | RTC | RTC Filter | RTC Reduction | RTC Filter Reduction |
| --- | ---: | ---: | ---: | ---: | ---: |
| Base input tokens | 211 | 127 | 101 | -40% | <strong><font color="#26C889">-52%</font></strong> |
| 1h cache-write tokens | 41,557 | 35,486 | 39,560 | <strong><font color="#26C889">-15%</font></strong> | -5% |
| Cache read/hit tokens | 1,493,195 | 906,149 | 770,735 | -39% | <strong><font color="#26C889">-48%</font></strong> |
| Output tokens | 16,969 | 11,656 | 11,946 | <strong><font color="#26C889">-31%</font></strong> | -30% |
| Total tokens | 1,551,933 | 953,417 | 822,342 | -39% | <strong><font color="#26C889">-47%</font></strong> |

### OpenClaw Average Per Task

| Metric | Legacy | RTC | RTC Filter | RTC Reduction | RTC Filter Reduction |
| --- | ---: | ---: | ---: | ---: | ---: |
| Cache-miss input tokens | 36,107 | 34,665 | 30,987 | -4% | <strong><font color="#26C889">-14%</font></strong> |
| Cache-hit input tokens | 1,273,830 | 734,925 | 591,334 | -42% | <strong><font color="#26C889">-54%</font></strong> |
| Reasoning tokens | 9,417 | 5,839 | 7,783 | <strong><font color="#26C889">-38%</font></strong> | -17% |
| Output tokens | 17,439 | 10,399 | 12,982 | <strong><font color="#26C889">-40%</font></strong> | -26% |
| Total tokens | 1,327,377 | 779,989 | 635,303 | -41% | <strong><font color="#26C889">-52%</font></strong> |

## Overview

Retrieval Token Cutter ships two local plugins:

| Host | Plugin | What it adds |
| --- | --- | --- |
| Claude Code | [claude-plugin/](claude-plugin/) | MCP tools for code search/edit plus prompt policy injection |
| OpenClaw | [openclaw-plugin/](openclaw-plugin/) | Native tools, prompt policy injection, and read/exec filtering |

Both plugins can start the local Retrieval Token Cutter backend and AGFS service
for you, then stop the services they started when the host exits.

![Runtime architecture](<docs/assets/readme/RTC/EN_Runtime Architecture.png>)

## Quickstart

Prepare a fresh checkout once:

```bash
git clone https://github.com/Calluking/RTC-Retrieval-Token-Cutter.git
cd RTC-Retrieval-Token-Cutter
./bootstrap.sh
```

`bootstrap.sh` is interactive for setup steps: if Ubuntu packages or Python
`.venv` are missing, it asks before installing anything. It also checks whether
OpenClaw and Claude Code are installed, then asks which integration to set up.
It does not ask you to type API keys into the installer.

Export your model and embedding settings:
(Use deepseek and text-embedding-3-small as example)
```bash
export DEEPSEEK_API_KEY="<your-deepseek-key>"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export OPENCLAW_MODEL="deepseek/deepseek-v4-flash"
export RTC_EMBEDDING_API_KEY="<your-embedding-key>"
export RTC_EMBEDDING_BASE_URL="https://api.openai-proxy.org"
export RTC_EMBEDDING_MODEL="text-embedding-3-small"
export ANTHROPIC_MODEL="haiku"
```

Then load the settings:

```bash
source setup_env.sh
```

`./bootstrap.sh` creates `.venv`, installs the runtime dependencies in
`requirements.txt`, and builds `agfs/build/agfs-server`. Full SWE-bench
validation is optional; install that heavier stack only when needed with
`./bootstrap.sh --install-swe-deps`.

![Fresh clone quickstart](<docs/assets/readme/RTC/EN_Fresh Clone Start.png>)

## Start Claude

From the project you want Claude to edit:

```bash
cd /path/to/project
claude --plugin-dir "$RTC_DIR/claude-plugin"
```

Do not pass `--mcp-config`; the Claude plugin owns its `.mcp.json`.

## Start OpenClaw

From the project you want OpenClaw to edit:

```bash
cd /path/to/project
openclaw chat --local
```

## Requirements

- Python 3.11+
- Go 1.22+
- Claude Code CLI, OpenClaw CLI, or both
- An OpenAI-compatible embedding endpoint and API key
- Conda, only if you use the SWE runner's default local validation environment

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

Local settings should come from your shell environment or shell profile, which
`setup_env.sh` imports before applying repo defaults. Do not commit real API
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
- [setup_env.sh](setup_env.sh): shared environment loader.
- [claude-plugin/prompts/code_policy_injection.txt](claude-plugin/prompts/code_policy_injection.txt): Claude policy prompt.
- [openclaw-plugin/prompts/code_policy_injection.txt](openclaw-plugin/prompts/code_policy_injection.txt): OpenClaw policy prompt.
- [docs/assets/readme/](docs/assets/readme/): generated README diagrams. Refresh with `python3 docs/assets/readme/generate_readme_diagrams.py`.
- [scripts/SWE/](scripts/SWE/): SWE Lite runners and reports.
- [LICENSE](LICENSE): Mulan Permissive Software License v2 (`MulanPSL-2.0`).

## SWE Lite Runner

The SWE runners build a task prompt and start Claude or OpenClaw
non-interactively. See [scripts/SWE/README.md](scripts/SWE/README.md) for the
six runner modes, run commands, output locations, and log checks.

## License

This project is licensed under the Mulan Permissive Software License v2
(`MulanPSL-2.0`). See [LICENSE](LICENSE).

## References

- [AGFS](https://github.com/c4pt0r/agfs): RTC bundles and builds the local AGFS
  server under [agfs/](agfs/) and uses `pyagfs` for local memory/file-service
  operations.
