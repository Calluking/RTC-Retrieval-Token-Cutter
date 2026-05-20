# SWE Lite Plain Claude Runner

This folder runs the same SWE-bench Lite task flow with plain Claude Code.

It does not load the Retrieval Token Cutter plugin and does not start RTC,
AGFS, or MCP services.

Install the repository dependencies from the repository root before using the
default local validation path:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The default derived local SWE-bench environment uses Conda. Set
`SWE_USE_DERIVED_LOCAL_ENV=0` for a smoke run that skips local env derivation,
or `SWE_SKIP_VALIDATION=1` to skip final validation.

## Run

From the repository root:

```bash
source scripts/SWE/claude/legacy/setup_swe_env.sh
SWE_USE_DERIVED_LOCAL_ENV=0 \
SWE_SKIP_VALIDATION=1 \
./scripts/SWE/claude/legacy/run_swe_task_lite_plain_claude.sh
```

To run a different SWE-bench Lite instance:

```bash
./scripts/SWE/claude/legacy/run_swe_task_lite_plain_claude.sh <instance_id>
```

## Outputs

Runs are written under:

```text
${XDG_CACHE_HOME:-~/.cache}/retrieval-token-cutter/swe/plain/output_logs/<timestamp>-swe-lite-plain-r<run>-p<pid>/
```

Set `SWE_OUTPUT_ROOT=/path/to/output_logs` to write runs somewhere else.

Useful files:

- `workspace/TASK.md`
- `logs/claude-code-debug.log`
- `logs/claude-stdout.log`
- `latest_session_render.txt`
- `validation.md`
- `validation.json`
