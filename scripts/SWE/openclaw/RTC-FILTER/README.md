# SWE Lite OpenClaw RTC-FILTER Runner

This runner is the OpenClaw counterpart of `scripts/SWE/claude/RTC-FILTER`.
It runs the same OpenClaw RTC plugin harness as `../RTC`, but uses a separate
cache/output namespace and enables the filtering prompt section by default.

Enabled by default:

- `RTC_INJECT_FILTERING_PROMPT=1`
- `RTC_FILTER_ENABLED=1`
- `RTC_FILTER_NATIVE_READ=1`
- `RTC_FILTER_NATIVE_BASH=1`

The actual native `read` and `exec` filters are implemented in
`openclaw-plugin/src/filter.ts`. The prompt injection is rendered through
`openclaw-plugin/src/policy.ts`, so the filtering-strategy text follows the
same environment toggle behavior as the Claude plugin.

## Run

From the repository root:

```bash
source scripts/SWE/openclaw/RTC-FILTER/setup_swe_env.sh
./scripts/SWE/openclaw/RTC-FILTER/run_swe_task_lite_openclaw_rtc_filter_plugin.sh
```

Run a specific SWE-bench Lite task:

```bash
./scripts/SWE/openclaw/RTC-FILTER/run_swe_task_lite_openclaw_rtc_filter_plugin.sh django__django-11019
```

For a faster smoke/debug run:

```bash
SWE_USE_DERIVED_LOCAL_ENV=0 \
SWE_SKIP_VALIDATION=1 \
./scripts/SWE/openclaw/RTC-FILTER/run_swe_task_lite_openclaw_rtc_filter_plugin.sh django__django-11019
```

## Output

Runs are written under:

```text
scripts/SWE/openclaw/RTC-FILTER/output_logs/<timestamp>-swe-lite-openclaw-rtc-r<run>-p<pid>/
```

Useful files:

- `workspace/TASK.md`: prompt sent to OpenClaw, including the filtering section.
- `latest_session_render.txt`: readable session summary.
- `openclaw_tool_summary.json`: parsed tool-call summary.
- `logs/openclaw-stdout.log`: OpenClaw non-interactive output.
- `logs/openclaw-plugin-runtime.json`: runtime plugin inspection.

`output_logs/latest` points to the newest run.

## Relation To RTC

This directory intentionally wraps `../RTC/run_swe_task_lite_openclaw_rtc_plugin.sh`
instead of duplicating the full harness. That keeps OpenClaw RTC and RTC-FILTER
behavior aligned while making the experiment mode explicit in paths, docs, and
default environment variables.
