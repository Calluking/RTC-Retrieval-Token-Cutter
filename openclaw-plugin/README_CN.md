# Retrieval Token Cutter OpenClaw 插件

这是 Retrieval Token Cutter 的原生 OpenClaw 插件，提供代码搜索和精确字符串替换编辑。

插件暴露的工具：

- `rtc_search_code`
- `rtc_edit_file`
- `rtc_index_codebase`
- `rtc_health`

OpenClaw 加载插件时，插件可以自动启动本地 RTC 和 AGFS 服务；OpenClaw 退出时，会停止由插件启动的服务。

对于代码相关 prompt，插件会注入策略，要求 agent 在大范围读取文件前调用 `rtc_search_code`，并在可行时用 `rtc_edit_file` 修改文件。

启用过滤时，插件还会 hook OpenClaw 原生的 `read` 和 `exec` 调用。整文件读取会被改写到 RTC 生成的过滤后文件；Python/pytest 测试、diff 等白名单长输出命令会被 wrapper 包起来，先经过 RTC 过滤再返回给 agent。被过滤的输出会包含取回原始输出的提示。

## 安装

在仓库根目录：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

把 embedding 密钥放在本机 shell 环境里，例如 `~/.bashrc`：

```bash
export RTC_EMBEDDING_API_KEY="<your-key>"
export RTC_EMBEDDING_BASE_URL="https://api.openai-proxy.org"
export RTC_EMBEDDING_MODEL="text-embedding-3-small"
```

然后以本地链接方式安装插件：

```bash
cd /path/to/retrieval-token-cutter
source setup_env.sh
openclaw plugins install --link ./openclaw-plugin --dangerously-force-unsafe-install
openclaw plugins enable retrieval-token-cutter
openclaw gateway restart
```

如果这个插件之前已经从另一个 checkout 安装过，先卸载旧注册项，再重新链接
当前 clone：

```bash
openclaw plugins uninstall retrieval-token-cutter --force
openclaw plugins install --link ./openclaw-plugin --dangerously-force-unsafe-install
```

OpenClaw 要求显式加上 unsafe-install 参数，是因为这个插件会通过 Node
child process API 启动本地 RTC/AGFS 服务。对于自动启动能力来说这是预期行为；
插件只会启动本仓库内的本地服务。

验证运行时是否加载：

```bash
openclaw plugins inspect retrieval-token-cutter --runtime --json
```

运行时输出应包含 `status: "loaded"`、服务 `retrieval-token-cutter`，以及这些工具：

```text
rtc_health
rtc_index_codebase
rtc_search_code
rtc_edit_file
```

## 配置

插件默认读取 `setup_env.sh` 和 `env.sh` 里的环境变量。

可选 OpenClaw 配置位置为 `plugins.entries.retrieval-token-cutter.config`：

```json
{
  "workspaceRoot": "/path/to/project",
  "rtcUrl": "http://127.0.0.1:8090",
  "autoStart": true,
  "autoStop": true,
  "injectCodePolicy": true,
  "filterEnabled": true,
  "filterNativeRead": true,
  "filterNativeExec": true
}
```

如果不设置 `workspaceRoot`，插件会依次使用 `RTC_WORKSPACE_ROOT` 和 OpenClaw 进程启动目录。

环境变量开关与 Claude 插件保持一致：

```bash
export RTC_FILTER_ENABLED=1
export RTC_FILTER_NATIVE_READ=1
export RTC_FILTER_NATIVE_BASH=1
```

把任意开关设为 `0`、`false`、`no` 或 `off` 可关闭对应层。

注入 prompt 里的过滤策略说明也和 Claude 一样由同一个变量控制：

```bash
export RTC_INJECT_FILTERING_PROMPT=1
```

默认不会把这段策略说明注入 prompt，但实际 filter hook 仍然可用。

## 启动 OpenClaw

OpenClaw 官方的 local embedded TUI 命令是：

```bash
openclaw chat
```

它等价于：

```bash
openclaw tui --local
```

使用 RTC 时，建议在目标项目目录启动，并传入新的 session 名，避免复用 `agent:<agent>:main` 历史：

```bash
cd /path/to/project
source /path/to/retrieval-token-cutter/setup_env.sh
export RTC_WORKSPACE_ROOT="$PWD"
openclaw chat --local --session "rtc-$(date +%s)"
```

然后正常提问：

```text
Fix the bug in the add function.
```

TUI 可能会折叠工具调用卡片。终端里没有直接看到 `rtc_search_code`，不代表工具没有被调用。

## 验证某次运行使用了搜索

找到最新的 OpenClaw session JSONL，并搜索 RTC 工具调用：

```bash
latest=$(ls -t ~/.openclaw/agents/*/sessions/*.jsonl | grep -v trajectory | head -1)
rg -n "rtc_search_code|rtc_edit_file|python -m pytest|Fix the bug" "$latest"
```

一次成功运行通常会包含这样的流程：

```text
TOOL CALL: rtc_search_code
TOOL RESULT: rtc_search_code
TOOL CALL: rtc_edit_file
TOOL RESULT: rtc_edit_file
TOOL CALL: exec
```

示例 `rtc_search_code` 参数：

```json
{
  "path": "/path/to/project",
  "query": "add function"
}
```
