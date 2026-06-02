# SWE-bench Lite Runners

[中文文档](README_CN.md)

This folder contains six SWE-bench Lite runners:

| Case | Script | RTC search | Filtering |
| --- | --- | --- | --- |
| Claude legacy | `scripts/SWE/claude/legacy/run_swe_task_lite_plain_claude.sh` | No | No |
| Claude RTC | `scripts/SWE/claude/RTC/run_swe_task_lite_rtc_plugin.sh` | Yes | No |
| Claude RTC-FILTER | `scripts/SWE/claude/RTC-FILTER/run_swe_task_lite_rtc_plugin.sh` | Yes | Yes |
| OpenClaw legacy | `scripts/SWE/openclaw/legacy/run_swe_task_lite_plain_openclaw.sh` | No | No |
| OpenClaw RTC | `scripts/SWE/openclaw/RTC/run_swe_task_lite_openclaw_rtc_plugin.sh` | Yes | No |
| OpenClaw RTC-FILTER | `scripts/SWE/openclaw/RTC-FILTER/run_swe_task_lite_openclaw_rtc_filter_plugin.sh` | Yes | Yes |

## Instructions

Start from the repository root:

```bash
cd /path/to/RTC-Retrieval-Token-Cutter
```

Prepare RTC once:

```bash
./bootstrap.sh
```

Load your local RTC settings:

```bash
source setup_env.sh
```

Run a task by passing the SWE-bench Lite instance id. If no id is passed, each
runner uses its own default task.

## Claude

Plain Claude:

```bash
./scripts/SWE/claude/legacy/run_swe_task_lite_plain_claude.sh django__django-10914
```

Claude with RTC search/edit:

```bash
./scripts/SWE/claude/RTC/run_swe_task_lite_rtc_plugin.sh django__django-10914
```

Claude with RTC search/edit and read/bash filtering:

```bash
./scripts/SWE/claude/RTC-FILTER/run_swe_task_lite_rtc_plugin.sh django__django-10914
```

## OpenClaw

Plain OpenClaw:

```bash
source scripts/SWE/openclaw/legacy/setup_swe_env.sh
./scripts/SWE/openclaw/legacy/run_swe_task_lite_plain_openclaw.sh django__django-10914
```

OpenClaw with RTC search/edit:

```bash
source scripts/SWE/openclaw/RTC/setup_swe_env.sh
./scripts/SWE/openclaw/RTC/run_swe_task_lite_openclaw_rtc_plugin.sh django__django-10914
```

OpenClaw with RTC search/edit and read/exec filtering:

```bash
source scripts/SWE/openclaw/RTC-FILTER/setup_swe_env.sh
./scripts/SWE/openclaw/RTC-FILTER/run_swe_task_lite_openclaw_rtc_filter_plugin.sh django__django-10914
```

## Quick Debug

Skip derived local environment setup and final validation:

```bash
SWE_USE_DERIVED_LOCAL_ENV=0 SWE_SKIP_VALIDATION=1 \
  ./scripts/SWE/claude/RTC/run_swe_task_lite_rtc_plugin.sh django__django-10914
```

Use the official Docker validator instead of local validation:

```bash
SWE_VALIDATION_FORCE_LOCAL=0 \
  ./scripts/SWE/claude/RTC/run_swe_task_lite_rtc_plugin.sh django__django-10914
```

The same environment variables work with the other runners.

## Output

Each runner writes to its own `output_logs` directory:

```text
scripts/SWE/claude/legacy/output_logs/
scripts/SWE/claude/RTC/output_logs/
scripts/SWE/claude/RTC-FILTER/output_logs/
scripts/SWE/openclaw/legacy/output_logs/
scripts/SWE/openclaw/RTC/output_logs/
scripts/SWE/openclaw/RTC-FILTER/output_logs/
```

Every output directory has a `latest` symlink:

```bash
ls -la scripts/SWE/claude/RTC/output_logs/latest
```

Useful files:

| File | Purpose |
| --- | --- |
| `workspace/` | Target repository after the agent edited it |
| `workspace/TASK.md` | Prompt given to the agent |
| `logs/claude-code-debug.log` | Claude debug log |
| `logs/claude-stdout.log` | Claude run output |
| `logs/openclaw-stdout.log` | OpenClaw run output |
| `latest_session_render.txt` | Readable session summary |
| `openclaw_tool_summary.json` | Parsed OpenClaw tool-call summary |
| `logs/retrieval-token-cutter-server.log` | RTC backend log |
| `validation.md` | Human-readable validation result |
| `validation.json` | Machine-readable validation result |

## Checks

Claude RTC search calls:

```bash
rg -n "Calling MCP tool: search_code|Tool 'search_code'" \
  scripts/SWE/claude/RTC/output_logs/latest/logs/claude-code-debug.log
```

Claude RTC search timings:

```bash
rg -n "code_semantic_search hybrid path|candidate_ingest_sec" \
  scripts/SWE/claude/RTC/output_logs/latest/logs/retrieval-token-cutter-server.log
```

OpenClaw RTC tool calls:

```bash
cat scripts/SWE/openclaw/RTC/output_logs/latest/openclaw_tool_summary.json
rg -n "rtc_search_code|rtc_edit_file" \
  scripts/SWE/openclaw/RTC/output_logs/latest/logs/*.jsonl
```

Filtering should only appear in `RTC-FILTER` runs:

```bash
rg -n "filter_bash|filter_read|FILTER|rtc_filter" \
  scripts/SWE/claude/RTC-FILTER/output_logs/latest/logs/*
```

Validation:

```bash
cat scripts/SWE/claude/RTC/output_logs/latest/validation.md
cat scripts/SWE/claude/RTC/output_logs/latest/validation.json
```
