# Prompt Inventory

A map of every place this repo constructs text that is sent to an LLM/agent.
Used to decide where the "caveman" compression style is injected.

Legend:
- **[TARGET]** — host coding agent prompt; caveman is injected on top of these.
- **[OUT OF SCOPE]** — RTC's own internal LLM calls. Most emit structured JSON,
  so caveman is intentionally NOT applied (would risk breaking JSON parsing).

The caveman style only affects the host agent's wording in its private thinking
and visible responses. It never touches code, diffs, file paths, error strings,
or destructive-action confirmations (see `prompts/caveman_injection.txt`).

---

## Host coding agent prompts — [TARGET]

These are injected into Claude / OpenClaw / the SWE task and are where caveman
saves tokens.

| File:line | What | Caveman injection point |
| --- | --- | --- |
| `claude-plugin/prompts/code_policy_injection.txt` | Code search/edit policy injected per user prompt | `caveman_prompt()` appended in `hook_compose()` |
| `claude-plugin/scripts/rtc_terminal.py:186` (`code_policy_prompt`) | Renders the policy text | new `caveman_prompt()` + `parse_caveman_block()` |
| `claude-plugin/scripts/rtc_terminal.py:620-647` (`hook_compose`) | `additionalContext` injected on `UserPromptSubmit` | caveman block appended here |
| `openclaw-plugin/prompts/code_policy_injection.txt` | OpenClaw copy of the policy | `loadCavemanPrompt()` |
| `openclaw-plugin/src/policy.ts` (`registerPolicyHook`) | `before_prompt_build` context injection | caveman block appended to `blocks` |
| `scripts/SWE/resolve_swe_lite_instance.py` (`build_prompt` + `main`) | SWE-bench Lite TASK prompt | `caveman_block()` appended to written prompt |
| `scripts/SWE-pro/resolve_swe_pro_instance.py` (`build_prompt` + `main`) | SWE-bench Pro TASK prompt | `caveman_block()` appended to written prompt |

### Caveman source of truth
- `prompts/caveman_injection.txt` (canonical, holds L1/L2/L3 blocks).
- `claude-plugin/prompts/caveman_injection.txt` (copy for the Claude plugin).
- `openclaw-plugin/prompts/caveman_injection.txt` (copy for the OpenClaw plugin).
- Keep all three in sync.

---

## RTC internal LLM prompts — [OUT OF SCOPE]

Left untouched. Most produce JSON or feed extraction/compression pipelines.

| File:line | What | Output |
| --- | --- | --- |
| `extraction/prompts/templates/extraction.yaml:19` | `system_prompt` for memory extraction | JSON / tool calls |
| `extraction/prompts/templates/extraction.yaml:161,382,391` | examples / conversation header / output-language instruction | JSON |
| `extraction/tools.py:110-136` | Phase 1 span-detection prompt | JSON |
| `extraction/tools.py:645-681` | Phase 2 extraction prompt builder | tool calls |
| `extraction/react_loop.py:228-396` | ReAct system prompt / nudges / safety reminder | tool calls |
| `extraction/prefetch.py:109-211` | existing-memory context injected as system msgs | JSON |
| `extraction/tool_collector.py:105-107` | tool-usage stats header | JSON |
| `session/compressor.py:87-101` | conversation -> two summaries | JSON |
| `session/rolling_compressor.py:78-91` | structured state extraction | JSON |
| `index/directory_summarizer.py:16-34` | aggregate child node summaries | text/JSON |
| `code-version/commit/archive_builder.py:234-239` | merge two memory descriptions | text |
| `providers/llm/openai_llm.py:144-148,460-469` | system msg for all `complete_json` calls | JSON |

### Tool-schema descriptions (function-calling) — [OUT OF SCOPE]
| File:line | What |
| --- | --- |
| `extraction/tool_schemas.py:31-271` | Pydantic tool + field descriptions |
| `extraction/schemas/definitions/*.yaml` | schema-registry descriptions |
| `claude-plugin/retrieval_token_cutter_mcp/server.py:261-421` | MCP tool descriptions |
| `openclaw-plugin/src/tools.ts:354-458` | OpenClaw tool descriptions |

---

## Setting

`RTC_CAVEMAN_LEVEL` (env): `0`=off, `1`=lite, `2`=full, `3`=ultra.
- Default exported in `setup_env.sh`.
- Mirrored in `RtcConfig.caveman_level` (`code-version/providers/unified_config.py`,
  YAML key `agent.caveman_level`) for visibility/logging.
- Read directly by `rtc_terminal.py`, `policy.ts`, and both SWE resolvers.
