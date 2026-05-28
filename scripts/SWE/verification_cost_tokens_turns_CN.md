# SWE 验证成本 / Token / 轮次

计价口径：Claude Haiku 4.5 按输入 $1/MTok、输出 $5/MTok、缓存读取 $0.10/MTok、5 分钟缓存写入 $1.25/MTok、1 小时缓存写入 $2/MTok 估算。DeepSeek V4 Flash 官方价格区分缓存命中输入、缓存未命中输入和输出；OpenClaw 日志已经记录 provider 成本，因此表格使用日志中的 DeepSeek 成本。

| run | model | turns | tool calls/results | input | output | cache read | cache write 5m | cache write 1h | total tokens | estimated/logged cost |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| claude_legacy | claude-haiku-4-5-20251001 | 40 / 88 | 39 / 39 | 622 | 29710 | 5036216 | 0 | 124051 | 5190599 | $0.900896 |
| claude_rtc | claude-haiku-4-5-20251001 | 28 / 75 | 27 / 27 | 537 | 37414 | 5791475 | 0 | 263079 | 6092505 | $1.292912 |
| openclaw_legacy | deepseek/deepseek-v4-flash | 1 / 30 | 32 / 32 | 33116 | 9553 | 934144 | 0 | 0 | 42664 | $0.009927 |
| openclaw_rtc | deepseek/deepseek-v4-flash | 1 / 14 | 14 / 14 | 44637 | 6939 | 552320 | 0 | 0 | 53247 | $0.009739 |

## DeepSeek 价格说明

是的，DeepSeek V4 Flash 会对缓存命中输入、缓存未命中输入和输出使用不同价格。官方当前价格为：缓存命中输入 $0.0028/MTok，缓存未命中输入 $0.14/MTok，输出 $0.28/MTok。输出价格是缓存未命中输入的 2 倍，而缓存命中输入便宜很多。

## 来源

- Claude pricing: https://platform.claude.com/docs/en/about-claude/pricing
- DeepSeek pricing: https://api-docs.deepseek.com/quick_start/pricing/
