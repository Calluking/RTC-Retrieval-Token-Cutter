# OpenClaw 11019 Tool Prompt Compare
Legacy run: `scripts/SWE/openclaw/legacy/output_logs/20260521-234516-swe-lite-openclaw-plain-r704-p37010`
RTC run: `scripts/SWE/openclaw/RTC/output_logs/20260521-225547-swe-lite-openclaw-rtc-r603-p20743`
## Summary
- Legacy tools: 28
- RTC tools: 33
- Only in legacy: []
- Only in RTC: ['rtc_edit_file', 'rtc_health', 'rtc_index_codebase', 'rtc_read', 'rtc_search_code']
- Common tools with changed prompt/schema: []

## Tool List
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

## RTC-only Tool Prompts

### `rtc_edit_file`

Description:

```text
Edit a file through exact string replacement after rtc_search_code. old_string must match exact text in the target file, similar to OpenClaw edit oldText. Normally build old_string by copying exact lines from rtc_search_code content_excerpt/local_snippet_fallback and call this directly without re-reading the same file. If exact text is missing after a focused search retry, use a narrow read.
```

Parameters:

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

Description:

```text
Check whether the local Retrieval Token Cutter backend is healthy.
```

Parameters:

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {}
}
```

### `rtc_index_codebase`

Description:

```text
Warm code indexing for a workspace. Normal rtc_search_code calls also index candidates automatically.
```

Parameters:

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

Description:

```text
Read file contents. For code tasks, do not use this on a file already returned by rtc_search_code with usable content_excerpt/local_snippet_fallback snippets; those snippets are exact file text and should be used directly for reasoning and rtc_edit_file.old_string. Use this only when RTC search misses the needed file or still lacks exact replacement context after a focused retry.
```

Parameters:

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

Description:

```text
Search repository source, tests, docs, and release notes with Retrieval Token Cutter. content_excerpt values are exact editable file text, not summaries; copy them directly into rtc_edit_file.old_string when possible. Do not re-read files already returned with usable snippets; if search misses or lacks exact context after a focused retry, use a narrow read.
```

Parameters:

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

## Common Tool Prompt Hashes
| Tool | Legacy SHA256 | RTC SHA256 |
|---|---|---|
| `agents_list` | `9dd7e02cc7fc` | `9dd7e02cc7fc` |
| `browser` | `86fbcdccf551` | `86fbcdccf551` |
| `canvas` | `d8b82d65f66b` | `d8b82d65f66b` |
| `cron` | `cb22bc4dc550` | `cb22bc4dc550` |
| `dir_fetch` | `0c0f11823bba` | `0c0f11823bba` |
| `dir_list` | `0bce7c701ee8` | `0bce7c701ee8` |
| `edit` | `73b7fbf99168` | `73b7fbf99168` |
| `exec` | `386fea724f74` | `386fea724f74` |
| `file_fetch` | `60b5964a6c77` | `60b5964a6c77` |
| `file_write` | `3c4f0bc57419` | `3c4f0bc57419` |
| `gateway` | `f968eadd606d` | `f968eadd606d` |
| `memory_get` | `2214a9f4bdd8` | `2214a9f4bdd8` |
| `memory_search` | `18fcb9e81e3a` | `18fcb9e81e3a` |
| `message` | `ad09f902f467` | `ad09f902f467` |
| `nodes` | `9f43066dd0bd` | `9f43066dd0bd` |
| `process` | `683d5b797721` | `683d5b797721` |
| `read` | `8818b4723b06` | `8818b4723b06` |
| `session_status` | `aa024ccb471e` | `aa024ccb471e` |
| `sessions_history` | `7edfdd43a0b5` | `7edfdd43a0b5` |
| `sessions_list` | `71f22c6729ed` | `71f22c6729ed` |
| `sessions_send` | `a51430582824` | `a51430582824` |
| `sessions_spawn` | `e43a4f95fa45` | `e43a4f95fa45` |
| `sessions_yield` | `294874ff1d75` | `294874ff1d75` |
| `subagents` | `b09fccf91078` | `b09fccf91078` |
| `tts` | `3af606ad6bc5` | `3af606ad6bc5` |
| `web_fetch` | `2d11181f79ea` | `2d11181f79ea` |
| `web_search` | `675bfd6a178e` | `675bfd6a178e` |
| `write` | `226b29695c91` | `226b29695c91` |
