# SWE Lite OpenClaw Legacy Runner

This folder runs the same SWE-bench Lite task flow with plain OpenClaw.

It does not load the Retrieval Token Cutter plugin and does not start RTC,
AGFS, MCP, or plugin-managed services.

If your personal OpenClaw config has local plugins enabled, the runner
temporarily clears local plugin load paths, disables the RTC plugin entry, and
sets `plugins.allow` to the current model provider for the duration of the run.
It restores the previous plugin config on exit.

Install repository dependencies from the repository root before using the
default local validation path:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

OpenClaw must already have a working model provider. This runner defaults to:

```bash
export OPENCLAW_MODEL="${OPENCLAW_MODEL:-deepseek/deepseek-v4-flash}"
```

## Run

From the repository root:

```bash
source scripts/SWE/openclaw/legacy/setup_swe_env.sh
./scripts/SWE/openclaw/legacy/run_swe_task_lite_plain_openclaw.sh
```

The default task is:

```bash
pallets__flask-4045
```

Run another task:

```bash
./scripts/SWE/openclaw/legacy/run_swe_task_lite_plain_openclaw.sh django__django-11133
```

## Validation

By default, `SWE_VALIDATION_FORCE_LOCAL=1`, so validation uses the task-specific
local environment derived from the official SWE-bench `TestSpec`.

Set `SWE_SKIP_VALIDATION=1` to skip final validation during quick smoke tests.

## Output

Runs are written under:

```text
scripts/SWE/openclaw/legacy/output_logs/<timestamp>-swe-lite-openclaw-plain-r<run>-p<pid>/
```

Set `SWE_OUTPUT_ROOT=/path/to/output_logs` to write runs somewhere else.

Useful files:

- `workspace/TASK.md`
- `logs/openclaw-stdout.log`
- `logs/openclaw-agent.json`
- `logs/<openclaw-session>.jsonl`
- `latest_session_render.txt`
- `openclaw_tool_summary.json`
- `validation.md`
- `validation.json`
