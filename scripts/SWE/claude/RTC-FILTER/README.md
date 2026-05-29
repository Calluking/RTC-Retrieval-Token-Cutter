# SWE Lite Claude Plugin Runner

It keeps the same SWE-bench Lite flow:

- resolve a SWE-bench Lite instance,
- clone the target repository at the base commit,
- write `TASK.md`,
- launch Claude Code,
- render the Claude transcript,
- optionally run validation.

The difference is service lifecycle and prompting: this runner loads `claude-plugin/`
and starts one isolated RTC/AGFS backend for the run before Claude begins. It
then disables plugin auto-start inside Claude so MCP calls use that same
instance, while cleanup still stops the backend. The MCP search/edit policy is
injected by the plugin from `claude-plugin/prompts/code_policy_injection.txt`,
so the SWE runner only writes the benchmark issue text and workspace paths.

## Setup

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

With `uv`, use the extras that match the runner bootstrap:

```bash
uv sync --extra mcp --extra swe
```

Create local `env.sh` with bootstrap, then edit it with local values:

```bash
./bootstrap.sh --skip-python --skip-agfs
$EDITOR env.sh
```

At minimum, set `RTC_EMBEDDING_API_KEY` for real RTC code search.

The default local SWE-bench environment derivation uses Conda because it adapts
the official SWE-bench `TestSpec` environment commands.

## Run

```bash
cd /path/to/retrieval-token-cutter
source scripts/SWE/claude/RTC-FILTER/setup_swe_env.sh
./scripts/SWE/claude/RTC-FILTER/run_swe_task_lite_rtc_plugin.sh
```

By default, `setup_swe_env.sh` sets `SWE_VALIDATION_FORCE_LOCAL=1`, so
validation runs in the local SWE-bench environment created for the task. This
avoids Docker-internal network failures on machines where containers cannot
reach GitHub. To use the official Docker harness instead:

```bash
SWE_VALIDATION_FORCE_LOCAL=0 ./scripts/SWE/claude/RTC-FILTER/run_swe_task_lite_rtc_plugin.sh
```

During the Claude fixing loop, the runner creates `workspace/RUN_IN_SWE_LOCAL_ENV.sh`
from the SWE-bench `TestSpec` before Claude starts. Claude is instructed to use
that helper for reproduction and verification:

```bash
./RUN_IN_SWE_LOCAL_ENV.sh pytest -q <target>
./RUN_IN_SWE_LOCAL_ENV.sh --reinstall pytest -q <target>
```

This is the closest practical interactive environment to the official harness:
same task-specific dependency recipe, but available before final validation.
The official Docker harness remains the stricter final check when the machine's
Docker network can reach the upstream repositories.

If your environment sets HTTP(S) or SOCKS proxies, the runner forces
`NO_PROXY`/`no_proxy` for loopback addresses so Claude, RTC, and AGFS can still
talk over `127.0.0.1`.

For a faster smoke run:

```bash
cd /path/to/retrieval-token-cutter
source scripts/SWE/claude/RTC-FILTER/setup_swe_env.sh
SWE_USE_DERIVED_LOCAL_ENV=0 \
SWE_SKIP_VALIDATION=1 \
./scripts/SWE/claude/RTC-FILTER/run_swe_task_lite_rtc_plugin.sh
```

## Outputs

Runs are written under:

```text
scripts/SWE/claude/RTC-FILTER/output_logs/<timestamp>-swe-lite-rtc-r<run>-p<pid>/
```

The latest run is linked at:

```text
scripts/SWE/claude/RTC-FILTER/output_logs/latest
```

Set `SWE_OUTPUT_ROOT=/path/to/output_logs` to write runs somewhere else.
The reusable cloned repository cache stays outside the project by default at
`${XDG_CACHE_HOME:-~/.cache}/retrieval-token-cutter/swe/rtc/cache/repo`.
Generated output, runtime caches, and moved workspace Git metadata are ignored
by the repository `.gitignore`.

Useful files:

- `workspace/TASK.md`
- `agfs-data/`
- `logs/claude-code-debug.log`
- `logs/claude-stdout.log`
- `logs/agfs-server.log`
- `logs/retrieval-token-cutter-server.log`
- `latest_session_render.txt`
- `validation.md`
- `validation.json`

For this runner, `RTC_RUNTIME_DIR` is set to the experiment directory, so
plugin runtime artifacts such as `agfs-data/`, `rtc-runtime/`, and backend
logs are kept with the run instead of in the default user cache.

After validation, `workspace/.git` is moved to `workspace.git` beside the
workspace. This preserves the generated checkout state for analysis, but keeps
editors from displaying every SWE run as a nested Git repository.

## Checks

Confirm the plugin loaded:

```bash
rg -n "Skill prompt|Loaded hooks|plugin:retrieval-token-cutter" "${SWE_OUTPUT_ROOT:-scripts/SWE/claude/RTC-FILTER/output_logs}/latest/logs/claude-code-debug.log"
```

Confirm MCP calls:

```bash
rg -n "mcp__plugin_retrieval-token-cutter_retrieval-token-cutter__(search_code|edit_file)|Tool 'search_code'|Tool 'edit_file'" "${SWE_OUTPUT_ROOT:-scripts/SWE/claude/RTC-FILTER/output_logs}/latest/logs/claude-code-debug.log"
```
