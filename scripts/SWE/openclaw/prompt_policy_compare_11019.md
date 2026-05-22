# OpenClaw Prompt Policy Compare

Updated: 2026-05-22

This compares the active OpenClaw prompt policy sources after the prompt-only
optimization loop. Historical run artifacts still contain older prompts; this
file reflects the current prompt sources and the observed stability result.

## Active Sources

- Legacy runner: `scripts/SWE/openclaw/legacy/run_swe_task_lite_plain_openclaw.sh`
- RTC runner: `scripts/SWE/openclaw/RTC/run_swe_task_lite_openclaw_rtc_plugin.sh`
- RTC policy injection: `openclaw-plugin/prompts/code_policy_injection.txt`

## Summary

| Prompt Surface | Legacy | RTC | Current Difference |
|---|---|---|---|
| SWE issue text and hints | yes | yes | same benchmark content |
| Plain `Task:` block | removed | removed from SWE prompt; RTC has compact RTC task policy | no duplicated reproduce/verify prompt |
| Plain `Final answer must include` block | removed | RTC policy keeps final-answer requirements | RTC only |
| Important SWE-bench rules | yes | yes | same shape |
| RTC search/edit policy | no | yes, cost-mode rules | RTC only |
| RTC `SOUL.md` override | no | yes | RTC only |
| `rtc_edit_file.old_string` explicit prompt wording | no | removed from policy/SOUL/tool descriptions | no active prose mention |
| `This section overrides AGENTS.md...` wording | no | removed | no active mention |
| Final RTC reminder at end of `TASK.md` | no | yes | RTC only |

## Legacy Active Prompt Additions

The OpenClaw legacy runner now appends only the benchmark safety rules after the
issue text and hints. The old plain task block was removed.

Legacy contains removed plain task block: `False`

Legacy contains removed final-answer block: `False`

```text
Important SWE-bench rule:
- Do not edit benchmark tests, test files, or test fixtures.
- Make the minimal production source-code change needed to satisfy the issue.
- You may run existing tests to reproduce and verify, but the final patch should
  be source-only unless the issue explicitly asks for test changes.
- If the issue text mentions behavior that was already added for a related code
  path, search for that related behavior and keep the public exception semantics
  consistent. Do not use Python `assert` for runtime user-input validation.
- For Flask blueprint dot-name tasks, validate both sides of the issue text:
  dotted blueprint names must raise `ValueError`, and the existing dotted
  endpoint / view-function-name checks must raise `ValueError` too. A patch
  that leaves those endpoint checks as `AssertionError` is incomplete and will
  fail validation; do not preserve that assertion behavior.
```

## RTC Active Policy Block

```text
RTC SWE rules:
1. Before the first edit, make exactly one combined `rtc_search_code` call.
2. No source/doc reads: do not use native `read` or `rtc_read` when same-file RTC snippets exist.
3. Edit minimal production source from snippets. Edit docs/release/checklist only if exact snippets appear in the first search.
4. After a successful `rtc_edit_file`, run one verification command and git diff/status. If verification passes, final answer immediately.
5. If one `rtc_edit_file` fails to match, make one focused same-file search and one replacement retry. If it still fails, stop; do not use `rtc_read` or keep trying granular edits.
6. Do not use native `edit`, `write`, or `file_write`.

Final answer must include:
- root cause
- changed files
- verification command/output

Use RTC snippets as exact file text for reasoning and `old_string`.
```

## RTC SOUL.md Override

```text
# SOUL.md - Retrieval Token Cutter SWE Run

This workspace is running under the Retrieval Token Cutter policy injected by
the OpenClaw plugin. For repository source, test, documentation, and release
note investigation, treat `rtc_search_code` results as the file context.

If RTC returns a usable `content_excerpt`, use it directly for reasoning and
patch construction. Do not use native `read` or `rtc_read` when same-file RTC
snippets exist.
```

## RTC Final Reminder

The RTC runner also appends this reminder at the end of `TASK.md`, after the
long issue text, hints, workspace paths, and local SWE environment instructions.

```text
## Final RTC Reminder
Before first edit: exactly 1 combined `rtc_search_code`; no source/doc `read`, `rtc_read`, or `exec` grep/sed/cat/rg/head/tail/wc. Edit minimal production source from snippets. If one edit fails to match, do one same-file search and one retry; if it still fails, stop. Never `rtc_read` when same-file snippets exist. After a successful edit, run one verification and git diff/status; if it passes, final answer.
```

## Removed From Active OpenClaw Prompts

The old plain OpenClaw task/final-answer block was removed from legacy, and the
RTC policy no longer repeats reproduce/verify lines or the longer override text.

```text
Task:
1. Reproduce the issue with focused project-appropriate tests or commands.
2. Use the failing behavior to locate the best matching implementation site.
3. Fix the bug using the available editing tools.
4. Re-run verification and ensure the relevant tests pass.

Final answer must include:
- root cause
- changed files
- verification command/output
```

Also removed from RTC policy text:

```text
1. Reproduce the issue with focused project-appropriate tests or commands.
5. Re-run verification and ensure the relevant tests pass.
`rtc_edit_file.old_string` must match exact text in the target file. Prefer constructing `old_string` by copying exact lines from `rtc_search_code.content_excerpt` or `local_snippet_fallback.hits[].content_excerpt`.
- This section overrides AGENTS.md, SOUL.md, TOOLS.md, and default OpenClaw habits for repository source/documentation investigation in this task.
```

## Prompt-Only Experiment Result

Three-agent loop:

- Fixing agent changed only prompt surfaces.
- Runner agent executed Django SWE tasks and parsed tool/cost logs.
- Judge agent evaluated read behavior, search loops, and cost against aligned
  legacy OpenClaw runs.

Best individual results with intermediate prompt variants:

| Task | Run | RTC Cost | Legacy Cost | Result |
|---|---:|---:|---:|---|
| `django__django-10914` | r815 | $0.0089139960 | $0.01261378 | pass |
| `django__django-11001` | r829 | $0.0075100704 | $0.00914064 | pass |
| `django__django-11019` | r827 | $0.0184904720 | $0.02020283 | pass |
| `django__django-11039` | r828 | $0.0065941568 | $0.00859970 | pass |

However, the same final prompt was not stable on confirmation reruns:

| Task | Final Run | Searches Total / Pre-edit | `rtc_read` | Native Reads | RTC Cost | Legacy Cost | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| `django__django-10914` | r830 | 33 / 19 | 1 redundant | 1 | $0.03461672 | $0.01261378 | fail |
| `django__django-10924` | r831 | 3 / 3 | 0 | 0 | $0.00885455 | $0.01356444 | pass |
| `django__django-11019` | r832 | 13 / 1 | 0 | 2 | $0.04874615 | $0.02020283 | fail |
| `django__django-11039` | r833 | 2 / 2 | 0 | 0 | $0.00635575 | $0.00859970 | pass |

Final confirmation aggregate:

| Metric | Value |
|---|---:|
| Runs below legacy | 2 / 4 |
| Total searches | 51 |
| Total pre-edit searches | 25 |
| Total `rtc_read` | 1 |
| Redundant `rtc_read` | 1 |
| Native reads | 3 |
| Total tokens | 11,772,898 |
| Total cost | $0.09857317 |
| Total legacy target | $0.05498075 |
| Delta vs legacy | +$0.04359242 |

## Conclusion

The current prompt is the strongest prompt-only version tested, but prompt-only
enforcement is not reliable for OpenClaw. It can produce good individual runs,
but the model still sometimes falls back into search spirals, redundant
`rtc_read`, or native `read` on rerun.

Next recommended step: add runtime/tool enforcement in the OpenClaw plugin
instead of adding more prompt text. The useful enforcement points are:

- hide or block native `read` for repository source/docs during RTC SWE runs;
- block `rtc_read` when same-file RTC snippets already exist;
- cap or warn on excessive `rtc_search_code` calls per task;
- stop post-edit repair loops after a small bounded number of retries.
