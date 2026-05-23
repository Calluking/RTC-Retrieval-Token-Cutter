# SWE Lite OpenClaw RTC Runner

This runner executes one SWE-bench Lite task with OpenClaw and the Retrieval Token Cutter OpenClaw plugin.

It will:

- resolve a SWE-bench Lite instance,
- clone and reset the benchmark repository,
- derive the local SWE-bench validation environment,
- link and enable `openclaw-plugin/`,
- run `openclaw agent --local` non-interactively,
- verify that OpenClaw actually called `rtc_search_code` and `rtc_edit_file`,
- run attached validation, and
- write logs, rendered session text, AGFS/RTC runtime data, and validation output under `output_logs/`.

## Requirements

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

OpenClaw must already have a working model provider. This runner defaults to:

```bash
export OPENCLAW_MODEL="${OPENCLAW_MODEL:-deepseek/deepseek-v4-flash}"
```

Keep embedding credentials in your shell environment, not in this repo:

```bash
export RTC_EMBEDDING_API_KEY="<your-key>"
export RTC_EMBEDDING_BASE_URL="https://api.openai-proxy.org"
export RTC_EMBEDDING_MODEL="text-embedding-3-small"
```

The runner does not require a preflight embedding probe by default. RTC search can still use its direct BM25/ctags fallback if an OpenAI-compatible endpoint does not expose `/v1/embeddings`. Set `RTC_EMBEDDING_PROBE_REQUIRED=1` to fail fast on embedding endpoint issues.

## Run

From the repository root:

```bash
source scripts/SWE/openclaw/RTC/setup_swe_env.sh
./scripts/SWE/openclaw/RTC/run_swe_task_lite_openclaw_rtc_plugin.sh
```

The default task is:

```bash
pallets__flask-4045
```

Run another task:

```bash
./scripts/SWE/openclaw/RTC/run_swe_task_lite_openclaw_rtc_plugin.sh django__django-11133
```

## Validation

By default, `SWE_VALIDATION_FORCE_LOCAL=1`, so validation uses the task-specific local environment derived from the official SWE-bench `TestSpec`.

To try the official Docker harness instead:

```bash
SWE_VALIDATION_FORCE_LOCAL=0 ./scripts/SWE/openclaw/RTC/run_swe_task_lite_openclaw_rtc_plugin.sh
```

## Output

Each run writes:

```text
scripts/SWE/openclaw/RTC/output_logs/<timestamp>-swe-lite-openclaw-rtc-r<run>-p<pid>/
```

Useful files:

- `workspace/`: task checkout after OpenClaw edits.
- `TASK.md`: prompt sent to OpenClaw.
- `logs/openclaw-stdout.log`: OpenClaw non-interactive output.
- `logs/openclaw-agent.json`: same captured output, useful for debugging JSON mode.
- `logs/openclaw-plugin-runtime.json`: runtime plugin inspection.
- `latest_session_render.txt`: readable session summary.
- `openclaw_tool_summary.json`: parsed tool-call summary.
- `validation.md`: human-readable validation result.
- `validation.json`: machine-readable validation result.
- `logs/validation-summary.json`: raw validator stdout.
- `logs/validation-stderr.log`: validator stderr.

`output_logs/latest` points to the newest run.

## Confirm RTC Tool Use

The runner fails if the OpenClaw session JSONL does not contain both:

```text
rtc_search_code
rtc_edit_file
```

Manual check:

```bash
cat scripts/SWE/openclaw/RTC/output_logs/latest/openclaw_tool_summary.json
rg -n "rtc_search_code|rtc_edit_file" scripts/SWE/openclaw/RTC/output_logs/latest/logs/*.jsonl
```

## Notes

The runner installs the OpenClaw plugin as a linked local plugin on each run:

```bash
openclaw plugins install --link ./openclaw-plugin --dangerously-force-unsafe-install
openclaw plugins enable retrieval-token-cutter
```

The runner itself uninstalls any existing `retrieval-token-cutter` registration
before installing the linked plugin so a stale OpenClaw plugin registration from
another checkout cannot override this run.

The unsafe-install flag is expected because the plugin starts local RTC/AGFS processes through Node's child process API.
