# OpenClaw RTC vs Legacy Token Composition

This report compares the first five Django SWE-bench Lite OpenClaw runs. RTC runs were rerun with the current settings; legacy uses the latest available matching completed legacy run for each task. Benchmark validation was skipped; agent-side verification still ran.

## Runs

| task | legacy run | rtc run |
|---|---|---|
| `django__django-10914` | `20260521-073017-swe-lite-openclaw-plain-r225-p174964` | `20260521-223946-swe-lite-openclaw-rtc-r601-p15220` |
| `django__django-10924` | `20260521-073528-swe-lite-openclaw-plain-r226-p176344` | `20260521-224750-swe-lite-openclaw-rtc-r602-p17974` |
| `django__django-11001` | `20260521-222250-swe-lite-openclaw-plain-r56-p10706` | `20260521-221245-swe-lite-openclaw-rtc-r56-p7424` |
| `django__django-11019` | `20260521-101713-swe-lite-openclaw-plain-r21019-p46354` | `20260521-225547-swe-lite-openclaw-rtc-r603-p20743` |
| `django__django-11039` | `20260521-133915-swe-lite-openclaw-plain-r22039-p78163` | `20260521-230857-swe-lite-openclaw-rtc-r604-p25878` |

## Cost And Token Summary

| setup | cost | turns | tool calls | failures | input | output | cache read | total tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| legacy | $0.05647 | 151 | 159 | 7 | 160,880 | 74,084 | 4,716,672 | 4,951,636 |
| rtc | $0.08047 | 144 | 153 | 2 | 256,594 | 78,162 | 8,093,056 | 8,427,812 |

RTC cost delta: `$0.02400` (42.5% over legacy).
RTC token delta: `3,476,176` total tokens (70.2% over legacy).

## Cost Composition

| setup | input cost | output cost | cache-read cost | total cost | input % | output % | cache-read % |
|---|---:|---:|---:|---:|---:|---:|---:|
| legacy | $0.02252 | $0.02074 | $0.01321 | $0.05647 | 39.9% | 36.7% | 23.4% |
| rtc | $0.03592 | $0.02189 | $0.02266 | $0.08047 | 44.6% | 27.2% | 28.2% |

Observation: output cost is not the whole story. RTC reduced some tool loops, but extra tool schemas, RTC policy text, search/read/edit payloads, and longer context growth raise input and cache-read spend.

## Per-Task Comparison

| task | legacy cost | rtc cost | delta | legacy turns/tools/fail | rtc turns/tools/fail | legacy tokens | rtc tokens | note |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `django__django-10914` | $0.00962 | $0.01765 | $0.00804 | 31/34/0 | 35/43/1 | 969,039 | 2,067,603 | legacy cheaper |
| `django__django-10924` | $0.01123 | $0.01480 | $0.00357 | 30/34/2 | 27/29/0 | 980,693 | 1,477,325 | legacy cheaper |
| `django__django-11001` | $0.00862 | $0.00953 | $0.00091 | 29/28/4 | 14/15/0 | 794,876 | 584,697 | legacy cheaper |
| `django__django-11019` | $0.01762 | $0.03002 | $0.01240 | 26/26/0 | 51/51/0 | 1,219,949 | 3,677,760 | legacy cheaper |
| `django__django-11039` | $0.00939 | $0.00846 | $-0.00092 | 35/37/1 | 17/15/1 | 987,079 | 620,427 | RTC cheaper |

## Tool Composition

| task | legacy tools | rtc tools |
|---|---|---|
| `django__django-10914` | `edit` 1, `exec` 23, `read` 10 | `exec` 23, `read` 1, `rtc_edit_file` 5, `rtc_read` 5, `rtc_search_code` 9 |
| `django__django-10924` | `edit` 1, `exec` 24, `read` 8, `write` 1 | `exec` 18, `rtc_edit_file` 1, `rtc_read` 1, `rtc_search_code` 9 |
| `django__django-11001` | `edit` 6, `exec` 16, `read` 6 | `exec` 7, `rtc_edit_file` 2, `rtc_read` 2, `rtc_search_code` 4 |
| `django__django-11019` | `edit` 5, `exec` 14, `read` 7 | `exec` 40, `rtc_edit_file` 4, `rtc_read` 3, `rtc_search_code` 4 |
| `django__django-11039` | `edit` 1, `exec` 25, `read` 7, `write` 4 | `exec` 11, `rtc_edit_file` 1, `rtc_search_code` 3 |

Notable issues:
- `django__django-10914` RTC still logged one native `read`, despite guard-mode intent.
- `django__django-11019` RTC made `40` `exec` calls, dominating the run. This is not a search/edit payload problem alone; the agent kept verifying/exploring through shell commands.
- RTC failures are lower overall (`2` vs `7`), so behavior is cleaner, but cleaner does not yet mean cheaper.

## Prompt Composition

| task | setup | system chars | project ctx | non-project ctx | skills | tool schemas | tool count | current prompt | final prompt | AGENTS | SOUL |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `django__django-10914` | legacy | 27,207 | 12,796 | 14,411 | 4,262 | 23,236 | 22 | 8,718 | 8,718 | 7,774 | 1,797 |
| `django__django-10914` | rtc | 26,505 | 11,586 | 14,919 | 4,589 | 31,230 | 33 | 15,228 | 15,228 | 7,774 | 617 |
| `django__django-10924` | legacy | 27,207 | 12,796 | 14,411 | 4,262 | 23,236 | 22 | 9,394 | 9,394 | 7,774 | 1,797 |
| `django__django-10924` | rtc | 26,505 | 11,586 | 14,919 | 4,589 | 31,230 | 33 | 15,904 | 15,904 | 7,774 | 617 |
| `django__django-11001` | legacy | 27,189 | 12,786 | 14,403 | 4,262 | 23,236 | 22 | 6,720 | 6,720 | 7,774 | 1,797 |
| `django__django-11001` | rtc | 26,487 | 11,576 | 14,911 | 4,589 | 31,230 | 33 | 13,223 | 13,223 | 7,774 | 617 |
| `django__django-11019` | legacy | 27,216 | 12,801 | 14,415 | 4,262 | 23,236 | 22 | 18,220 | 18,220 | 7,774 | 1,797 |
| `django__django-11019` | rtc | 26,505 | 11,586 | 14,919 | 4,589 | 31,230 | 33 | 24,727 | 24,727 | 7,774 | 617 |
| `django__django-11039` | legacy | 27,216 | 12,801 | 14,415 | 4,262 | 23,236 | 22 | 4,246 | 4,245 | 7,774 | 1,797 |
| `django__django-11039` | rtc | 26,505 | 11,586 | 14,919 | 4,589 | 31,230 | 33 | 10,753 | 10,752 | 7,774 | 617 |

## Are The Prompts The Same?

No. The benchmark issue text and local SWE environment instructions are mostly the same between legacy and RTC, but RTC prepends a substantial Retrieval Token Cutter policy block and changes the workspace guidance. OpenClaw also sees a different tool schema set.

Main differences:
- RTC adds a `[Retrieval Token Cutter]` task block before the normal SWE prompt.
- RTC requires `rtc_search_code` before editing source/code files.
- RTC forbids OpenClaw built-in `edit`, `write`, and `file_write` for source/code changes.
- RTC instructs the model to use `rtc_edit_file` and construct `old_string` from `rtc_search_code.content_excerpt`.
- RTC adds an OpenClaw context override for `AGENTS.md`, `SOUL.md`, `TOOLS.md`, and default OpenClaw habits.
- RTC says native `read` should not be used for repo source/docs, and fallback should be `rtc_read`.
- RTC adds an efficiency policy and search-limit policy.
- RTC changes injected `SOUL.md`: legacy SOUL is larger and general OpenClaw persona text; RTC SOUL is shorter and RTC-specific.
- RTC tool schemas are larger because OpenClaw also sees `rtc_read`, `rtc_health`, `rtc_index_codebase`, `rtc_search_code`, and `rtc_edit_file`; tool schema chars are typically about `31,230` for RTC vs `23,236` for legacy, an ~8k char fixed overhead every run.

### RTC-Only Prompt Injection

Representative prefix from `django__django-11001` RTC final prompt:
```text
[Retrieval Token Cutter]
Task:
1. Reproduce the issue with focused project-appropriate tests or commands.
2. Use `rtc_search_code` for source, test, documentation, and release-note discovery.
3. Use the returned snippets as your file context for files found by RTC search; if RTC search does not find a usable file/snippet, fall back narrowly.
4. Fix the bug using `rtc_edit_file` rather than broad direct file editing.
5. Re-run verification and ensure the relevant tests pass.

Final answer must include:
- root cause
- changed files
- verification command/output

## RTC requirement
Before you edit any source/code file, call the Retrieval Token Cutter tool `rtc_search_code` at least once.
Use `path` as the workspace root and write focused semantic/text queries for the exact symbol, setting, error, doc heading, or behavior.
Compare multiple top chunk hits, then patch only the best-matching files.
Do not use OpenClaw's built-in `edit`, `write`, or `file_write` tools for source/code changes in this task.
Treat `rtc_edit_file` as the required edit tool for source/code files found through RTC.
`rtc_edit_file.old_string` must match exact text in the target file. Prefer constructing `old_string` by copying exact lines from `rtc_search_code.content_excerpt` or `local_snippet_fallback.hits[].content_excerpt`.

## OpenClaw context override
- This section overrides AGENTS.md, SOUL.md, TOOLS.md, and default OpenClaw habits for repository source/documentation investigation in this task.
- For this task, `rtc_search_code` output counts as reading the source, tests, docs, and release notes.
- If any OpenClaw workspace/persona guidance says to "read the file", "check the context", or "read docs/source/types first", satisfy that guidance with `rtc_search_code` snippets.
- Do not call OpenClaw native `read` for repository source/docs in this task. If a narrow fallback read is truly needed, use `rtc_read`.
- Do not immediately call `rtc_read`, `file_fetch`, `dir_fetch`, or shell text readers on a file already returned by `rtc_search_code` with a usable `content_excerpt` or `local_snippet_fallback` snippet.
- If native `read` is blocked, follow the guard: use the RTC snippet, run one more focused `rtc_search_code` query, or call `rtc_read` only for a narrow fallback when RTC does not provide exact text.
- A file that appears only in `candidate_paths` is a lead, not usable file context. If there is no usable snippet for that file, one narrow read is allowed.
- If RTC search returns the target file with a usable snippet, use that snippet directly for reasoning and `old_string` construction.
- If RTC search misses the needed file, returns no usable snippet, or the exact replacement cannot be constructed after one more focused `rtc_search_code`, use the smallest targeted `rtc_read` needed to proceed.
- After RTC identifies a target file, prefer the returned `content_excerpt`, `start_line`, `end_line`, and `uri` as your file context.
- If `rtc_search_code` returns `local_snippet_fallback.hits`, treat those snippets exactly like normal RTC search hits and use them for `old_string` construction.
- Treat `rtc_search_code.content_excerpt` as exact editable file text, not as a summary. You may copy its lines directly into `rtc_edit_file.old_string`.
- Source/doc edit sequence should normally be: `rtc_search_code` -> `rtc_edit_file` -> verification command.
- Line numbers alone are not a reason to re-read a file already returned by RTC search; use RTC snippet `start_line`/`end_line` metadata when it is sufficient.
- Allowed `exec` uses: run reproduction commands, tests, lint/build checks, git diff/status, or environment diagnostics. Avoid using `exec` to search or print repository source/docs when RTC search has already returned the relevant file.
- You may pipe test/build output or `git diff` output through `tail`/`head` to keep command output short.

## RTC efficiency policy (turn/token reduction)
- `rtc_search_code` replaces broad `grep`, exploratory native `read`, and "open the file to inspect it" loops.
- Prefer exactly one focused `rtc_search_code` call. Use a second only if the first result clearly misses the target.
- After a good search hit, your default next source-code action is `rtc_edit_file`, not `rtc_read`.
- The snippets returned by `rtc_search_code` are exact file text and are enough context for small and medium patches. Build `old_string` directly from the snippet when possible.
- Do not call `rtc_read` just to confirm a file that search already identified.
- If a snippet is too short to form an exact `old_string`, first run another focused `rtc_search_code` for that file, symbol, heading, or nearby phrase. If that still fails, use one narrow `rtc_read`.
- For documentation tasks, treat `.txt` docs and release notes as source. Search them with RTC first; use `rtc_read` only when RTC search does not provide usable context.
- Keep visible code low: search snippets first, then exact edit, then tests.
- If `rtc_edit_file` repor
```

## Why RTC Still Costs More

The five-run aggregate shows RTC has slightly fewer turns/tools but much larger input/cache-read totals:
- Input tokens: legacy `160,880` vs RTC `256,594`.
- Cache-read tokens: legacy `4,716,672` vs RTC `8,093,056`.
- Output tokens: legacy `74,084` vs RTC `78,162`.

This means RTC is paying for repeated large context, not just final answers. The fixed overhead is visible in prompt composition: RTC has about 8k more tool-schema chars plus the policy injection. Dynamic overhead comes from `rtc_search_code` / `rtc_read` outputs and repeated verification loops, especially `11019`.

## Suggested Next Cuts

1. Shrink RTC prompt injection by 50-70%; keep only hard requirements and remove repeated wording.
2. Remove unused RTC tools from OpenClaw registration during SWE runs: likely hide `rtc_health` and `rtc_index_codebase` from the agent after startup.
3. Reduce `rtc_search_code` output further to only `hit_count`, `file`, `start_line`, `end_line`, `content_excerpt`; no candidate/debug fields by default.
4. Investigate why `10914` allowed native `read` despite guard mode.
5. Add a verification budget instruction for OpenClaw RTC, because `11019` spent `40` exec calls.
6. Consider disabling general OpenClaw skills/tools for SWE runs if possible; both legacy and RTC carry many unrelated schemas, but RTC pays extra on top.
