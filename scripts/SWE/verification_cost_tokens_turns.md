# SWE Verification Cost / Tokens / Turns

Pricing used: Claude Haiku 4.5 = $1/MTok input, $5/MTok output, $0.10/MTok cache read, $1.25/MTok 5m cache write, $2/MTok 1h cache write. DeepSeek V4 Flash official pricing separates cache-hit input, cache-miss input, and output; OpenClaw logs already report provider cost, so the table uses logged DeepSeek cost.

| run | model | turns | tool calls/results | input | output | cache read | cache write 5m | cache write 1h | total tokens | estimated/logged cost |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| claude_legacy | claude-haiku-4-5-20251001 | 40 / 88 | 39 / 39 | 622 | 29710 | 5036216 | 0 | 124051 | 5190599 | $0.900896 |
| claude_rtc | claude-haiku-4-5-20251001 | 28 / 75 | 27 / 27 | 537 | 37414 | 5791475 | 0 | 263079 | 6092505 | $1.292912 |
| openclaw_legacy | deepseek/deepseek-v4-flash | 1 / 30 | 32 / 32 | 33116 | 9553 | 934144 | 0 | 0 | 42664 | $0.009927 |
| openclaw_rtc | deepseek/deepseek-v4-flash | 1 / 14 | 14 / 14 | 44637 | 6939 | 552320 | 0 | 0 | 53247 | $0.009739 |

## DeepSeek Pricing Note
Yes. DeepSeek V4 Flash charges different prices for cache-hit input, cache-miss input, and output. Official current rates are $0.0028/MTok cache-hit input, $0.14/MTok cache-miss input, and $0.28/MTok output. Output is 2x cache-miss input, and cache-hit input is much cheaper.

## Sources
- Claude pricing: https://platform.claude.com/docs/en/about-claude/pricing
- DeepSeek pricing: https://api-docs.deepseek.com/quick_start/pricing/
