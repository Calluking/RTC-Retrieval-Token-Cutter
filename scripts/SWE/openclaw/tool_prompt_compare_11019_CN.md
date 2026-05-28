# OpenClaw 11019 工具 Prompt 对比

Legacy run: `scripts/SWE/openclaw/legacy/output_logs/20260521-234516-swe-lite-openclaw-plain-r704-p37010`

RTC run: `scripts/SWE/openclaw/RTC/output_logs/20260521-225547-swe-lite-openclaw-rtc-r603-p20743`

## 摘要

- Legacy tools: 28
- RTC tools: 33
- 仅 legacy 有：[]
- 仅 RTC 有：`rtc_edit_file`、`rtc_health`、`rtc_index_codebase`、`rtc_read`、`rtc_search_code`
- prompt/schema 发生变化的共同工具：[]

## 工具列表

| Tool | Legacy | RTC | Changed common schema |
|---|---:|---:|---:|
| `agents_list` | yes | yes | no |
| `browser` | yes | yes | no |
| `canvas` | yes | yes | no |
| `cron` | yes | yes | no |
| `dir_fetch` | yes | yes | no |
| `dir_list` | yes | yes | no |
| `edit` | yes | yes | no |
| `exec` | yes | yes | no |
| `file_fetch` | yes | yes | no |
| `file_write` | yes | yes | no |
| `gateway` | yes | yes | no |
| `memory_get` | yes | yes | no |
| `memory_search` | yes | yes | no |
| `message` | yes | yes | no |
| `nodes` | yes | yes | no |
| `process` | yes | yes | no |
| `read` | yes | yes | no |
| `rtc_edit_file` | no | yes | no |
| `rtc_health` | no | yes | no |
| `rtc_index_codebase` | no | yes | no |
| `rtc_read` | no | yes | no |
| `rtc_search_code` | no | yes | no |
| `session_status` | yes | yes | no |
| `sessions_history` | yes | yes | no |
| `sessions_list` | yes | yes | no |
| `sessions_send` | yes | yes | no |
| `sessions_spawn` | yes | yes | no |
| `sessions_yield` | yes | yes | no |
| `subagents` | yes | yes | no |
| `tts` | yes | yes | no |
| `web_fetch` | yes | yes | no |
| `web_search` | yes | yes | no |
| `write` | yes | yes | no |

## RTC 专属工具 Prompt

### `rtc_edit_file`

说明：

```text
Edit a file through exact string replacement after rtc_search_code. old_string must match exact text in the target file, similar to OpenClaw edit oldText. Normally build old_string by copying exact lines from rtc_search_code content_excerpt/local_snippet_fallback and call this directly without re-reading the same file. If exact text is missing after a focused search retry, use a narrow read.
```

参数：

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "file_path": {
      "type": "string",
      "description": "Absolute or workspace-relative file path."
    },
    "old_string": {
      "type": "string",
      "description": "Exact text to replace."
    },
    "new_string": {
      "type": "string",
      "description": "Replacement text."
    },
    "workspace_root": {
      "type": "string",
      "description": "Workspace root. Leave empty for the configured workspace."
    },
    "replace_all": {
      "type": "boolean",
      "description": "Replace every occurrence."
    }
  },
  "required": [
    "file_path",
    "old_string",
    "new_string"
  ]
}
```

### `rtc_health`

说明：

```text
Check whether the local Retrieval Token Cutter backend is healthy.
```

参数：

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {}
}
```

### `rtc_index_codebase`

说明：

```text
Warm code indexing for a workspace. Normal rtc_search_code calls also index candidates automatically.
```

参数：

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "path": {
      "type": "string",
      "description": "Workspace root. Leave empty for the configured workspace."
    },
    "force": {
      "type": "boolean",
      "description": "Reserved re-index flag."
    }
  }
}
```

### `rtc_read`

说明：

```text
Read file contents. For code tasks, do not use this on a file already returned by rtc_search_code with usable content_excerpt/local_snippet_fallback snippets; those snippets are exact file text and should be used directly for reasoning and rtc_edit_file.old_string. Use this only when RTC search misses the needed file or still lacks exact replacement context after a focused retry.
```

参数：

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "path": {
      "type": "string",
      "description": "Path to the file to read, relative to the configured workspace or absolute inside it."
    },
    "offset": {
      "type": "number",
      "description": "Optional 1-indexed starting line."
    },
    "limit": {
      "type": "number",
      "description": "Optional maximum number of lines."
    }
  },
  "required": [
    "path"
  ]
}
```

### `rtc_search_code`

说明：

```text
Search repository source, tests, docs, and release notes with Retrieval Token Cutter. content_excerpt values are exact editable file text, not summaries; copy them directly into rtc_edit_file.old_string when possible. Do not re-read files already returned with usable snippets; if search misses or lacks exact context after a focused retry, use a narrow read.
```

参数：

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "query": {
      "type": "string",
      "description": "Natural language, symbol, or keyword query."
    },
    "path": {
      "type": "string",
      "description": "Workspace root. Leave empty for the configured workspace."
    },
    "limit": {
      "type": "number",
      "minimum": 1,
      "maximum": 100,
      "description": "Max hits."
    },
    "glob_patterns": {
      "type": "string",
      "description": "Optional comma-separated glob patterns, e.g. src/**/*.py or docs/**/*.txt."
    },
    "grep_terms": {
      "type": "string",
      "description": "Optional comma-separated literal terms to require in results."
    }
  },
  "required": [
    "query"
  ]
}
```

## 共同工具 Prompt Hash

共同工具在 legacy 和 RTC 中的 schema/prompt hash 相同，没有变化。原始英文报告中保留了每个工具的 SHA256 前缀，便于审计；核心结论是 RTC 的额外 prompt 面主要来自 5 个 RTC 专属工具，而不是已有 OpenClaw 工具 schema 的变化。
