# Caveman Token-Savings Experiment Runbook

Goal: measure how much the caveman style cuts token usage on top of RTC, by
sweeping `RTC_CAVEMAN_LEVEL` (0 baseline -> 1 -> 2 -> 3) over a fixed set of
SWE-bench instances and comparing token counts.

Run this on a machine that already has a working RTC env (API keys, embeddings,
Docker for SWE). No live LLM calls are made on the dev machine that authored
this; the code is wired and ready to test.

## What changes per level

`RTC_CAVEMAN_LEVEL` selects a block from `prompts/caveman_injection.txt`:

| Level | Style | Notes |
| --- | --- | --- |
| 0 | off | No caveman block injected (baseline). |
| 1 | lite | Drop filler/hedging, keep full sentences. |
| 2 | full | Drop articles, fragments OK, short synonyms. |
| 3 | ultra | Abbreviate prose words, causal arrows, one word when enough. |

All levels preserve code, diffs, file paths, exact error strings, and
destructive-action confirmations verbatim.

## Setup

```bash
cd /path/to/RTC-Retrieval-Token-Cutter
./bootstrap.sh --install-swe-deps   # once
source setup_env.sh
```

Pick a small, fixed instance list so runs are comparable, e.g.:

```bash
INSTANCES=(django__django-10914 sympy__sympy-20590 pytest-dev__pytest-5103)
```

## Sweep

For each level, run the same instances with the same runner. Example using the
Claude RTC runner (swap for any runner in `scripts/SWE/README.md`):

```bash
for LEVEL in 0 1 2 3; do
  export RTC_CAVEMAN_LEVEL=$LEVEL
  for IID in "${INSTANCES[@]}"; do
    ./scripts/SWE/claude/RTC/run_swe_task_lite_rtc_plugin.sh "$IID"
  done
done
```

Notes:
- Restart the RTC backend (or unset/reset) between levels if it caches config;
  the plugins read `RTC_CAVEMAN_LEVEL` from the environment at prompt-build time,
  so re-`export` before each batch is enough for the plugin injection.
- To confirm the level reached the agent, dry-render the Claude policy:

```bash
RTC_CAVEMAN_LEVEL=2 python claude-plugin/scripts/rtc_terminal.py render-code-policy
```

  Level 0 prints only the code policy (no caveman block); levels 1-3 append the
  matching block.

## Measure tokens

Per run, capture token counts from the RTC backend:

```bash
curl -s "$RTC_URL/api/v1/token_stats" | tee "tokens_level${RTC_CAVEMAN_LEVEL}_${IID}.json"
```

This returns cumulative `input_tokens`, `output_tokens`, `embed_tokens`,
`llm_calls` (see `code-version/server/app.py` `/api/v1/token_stats` and
`providers/token_tracker.py`). For host-agent token usage, also read the agent's
own session output under
`scripts/SWE/<agent>/<mode>/output_logs/latest/` (transcript + any reported
usage), since the caveman effect is largest on the host agent's thinking and
responses, not RTC's internal calls.

Snapshot/reset between instances if you want per-instance deltas rather than
cumulative totals.

## Compare

Build a small table per (level, instance):

| Level | Instance | Input tok | Output tok | Total tok | Resolved? |
| --- | --- | --- | --- | --- | --- |
| 0 | ... | ... | ... | ... | y/n |
| 1 | ... | ... | ... | ... | y/n |
| 2 | ... | ... | ... | ... | y/n |
| 3 | ... | ... | ... | ... | y/n |

Watch two things together:
1. Token reduction vs level 0.
2. Resolution rate — ultra (3) may save the most tokens but risks hurting task
   success. Pick the level with the best savings that keeps resolution stable.
