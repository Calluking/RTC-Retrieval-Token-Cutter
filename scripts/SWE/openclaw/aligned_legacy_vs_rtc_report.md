# OpenClaw Legacy vs RTC, Aligned Runner

Date: 2026-05-21

This compares the first five Django SWE-Lite tasks after rewriting the OpenClaw
legacy runner from the RTC runner, with the RTC plugin disabled. Validation was
skipped for these runs (`SWE_SKIP_VALIDATION=1`); each agent still ran its own
reproduction and verification commands inside the task-local SWE environment.

## Runner Alignment

- Legacy runner: `scripts/SWE/openclaw/legacy/run_swe_task_lite_plain_openclaw.sh`
- RTC runner: `scripts/SWE/openclaw/RTC/run_swe_task_lite_rtc_openclaw.sh`
- The legacy runner now keeps the RTC runner's SWE workspace setup, local
  SWE-bench environment setup, logging, session render, JSONL capture, and tool
  summary flow.
- The legacy runner disables the `retrieval-token-cutter` OpenClaw plugin and
  uses the plain SWE prompt without RTC-specific tool requirements.

## Cost And Token Comparison

| Task | Setup | Turns | Tool Calls | Tool Failures | Total Tokens | Input | Output | Cache Read | Cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| django__django-10914 | legacy | 36 | 43 | 2 | 1,388,940 | 41,868 | 10,752 | 1,336,320 | $0.01261378 |
| django__django-10914 | RTC | 35 | 43 | 1 | 2,067,603 | 64,062 | 11,093 | 1,992,448 | $0.01765357 |
| django__django-10924 | legacy | 47 | 46 | 0 | 1,665,844 | 35,626 | 14,474 | 1,615,744 | $0.01356444 |
| django__django-10924 | RTC | 27 | 29 | 0 | 1,477,325 | 49,679 | 13,886 | 1,413,760 | $0.01480167 |
| django__django-11001 | legacy | 31 | 30 | 2 | 946,890 | 32,107 | 7,519 | 907,264 | $0.00914064 |
| django__django-11001 | RTC | 14 | 15 | 0 | 584,697 | 42,694 | 7,347 | 534,656 | $0.00953136 |
| django__django-11019 | legacy | 42 | 41 | 1 | 2,153,366 | 48,588 | 27,082 | 2,077,696 | $0.02020283 |
| django__django-11019 | RTC | 51 | 51 | 0 | 3,677,760 | 61,766 | 40,570 | 3,575,424 | $0.03001803 |
| django__django-11039 | legacy | 32 | 31 | 0 | 928,652 | 28,387 | 7,593 | 892,672 | $0.00859970 |
| django__django-11039 | RTC | 17 | 15 | 1 | 620,427 | 38,393 | 5,266 | 576,768 | $0.00846445 |

## Delta, RTC Minus Legacy

| Task | Cost Delta | Token Delta | Turn Delta | Tool Call Delta |
|---|---:|---:|---:|---:|
| django__django-10914 | +$0.00503980 | +678,663 | -1 | 0 |
| django__django-10924 | +$0.00123722 | -188,519 | -20 | -17 |
| django__django-11001 | +$0.00039072 | -362,193 | -17 | -15 |
| django__django-11019 | +$0.00981520 | +1,524,394 | +9 | +10 |
| django__django-11039 | -$0.00013525 | -308,225 | -15 | -16 |

## Totals

| Setup | Total Cost | Total Tokens |
|---|---:|---:|
| legacy | $0.06412139 | 7,083,692 |
| RTC | $0.08046908 | 8,427,812 |
| RTC - legacy | +$0.01634769 | +1,344,120 |

## Notes

- The aligned legacy prompt/tool schema is now much closer to RTC: legacy tool
  schema is about 29.5k chars, while RTC is about 31.2k chars.
- RTC reduced turns and tool calls on `10924`, `11001`, and `11039`, but
  `10914` and especially `11019` still consumed more cache-read and total tokens.
- This means the remaining gap is no longer just an unfair legacy tool allow-list
  difference; task behavior and RTC search/edit flow still need tuning.
