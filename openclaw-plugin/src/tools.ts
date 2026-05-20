import fs from "node:fs/promises";
import path from "node:path";
import type { ResolvedConfig } from "./config.ts";
import { identityFields, postJson, getJson } from "./http.ts";
import { resolveInside } from "./paths.ts";

const IDENT = "[A-Za-z_][A-Za-z0-9_]*";

function canonicalCodeQuery(query: string): string {
  const q = (query || "").trim();
  const patterns: Array<[RegExp, (symbol: string) => string]> = [
    [new RegExp(`^function\\s+(${IDENT})$`, "i"), (symbol) => `${symbol} function`],
    [new RegExp(`^def\\s+(${IDENT})$`, "i"), (symbol) => `${symbol} function`],
    [new RegExp(`^async\\s+function\\s+(${IDENT})$`, "i"), (symbol) => `${symbol} async function`],
    [new RegExp(`^async\\s+def\\s+(${IDENT})$`, "i"), (symbol) => `${symbol} async function`],
    [new RegExp(`^type\\s+(${IDENT})$`, "i"), (symbol) => `${symbol} type`],
  ];
  for (const [pattern, rewrite] of patterns) {
    const match = pattern.exec(q);
    if (match) return rewrite(match[1]);
  }
  return q;
}

function workspaceRoot(config: ResolvedConfig, requested?: string): string {
  const raw = (requested || "").trim();
  if (!raw || ["$WORK_DIR", "${WORK_DIR}", "$PWD", "${PWD}", "$RTC_WORKSPACE_ROOT", "${RTC_WORKSPACE_ROOT}"].includes(raw)) {
    return config.workspaceRoot;
  }
  return path.resolve(raw);
}

function prettyJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function toolResult(value: unknown): unknown {
  const text = typeof value === "string" ? value : prettyJson(value);
  return {
    content: [{ type: "text", text }],
  };
}

function paramsFromArgs<T>(arg1: unknown, arg2: unknown): T {
  return ((arg2 ?? arg1 ?? {}) as T);
}

export function registerRtcTools(api: any, config: ResolvedConfig, ensureBackend?: () => Promise<void>): void {
  const register = (tool: Record<string, unknown>, names: string[]) => {
    api.registerTool(tool, { names, name: names[0] });
  };

  register(
    {
      name: "rtc_health",
      label: "RTC Health",
      description: "Check whether the local Retrieval Token Cutter backend is healthy.",
      parameters: { type: "object", additionalProperties: false, properties: {} },
      async execute() {
        await ensureBackend?.();
        return toolResult(await getJson(config, "/api/v1/health", 5000));
      },
    },
    ["rtc_health"],
  );

  register(
    {
      name: "rtc_index_codebase",
      label: "RTC Index Codebase",
      description:
        "Warm code indexing for a workspace. Normal rtc_search_code calls also index candidates automatically.",
      parameters: {
        type: "object",
        additionalProperties: false,
        properties: {
          path: { type: "string", description: "Workspace root. Leave empty for the configured workspace." },
          force: { type: "boolean", description: "Reserved re-index flag." },
        },
      },
      async execute(arg1: unknown, arg2: unknown) {
        await ensureBackend?.();
        const params = paramsFromArgs<{ path?: string; force?: boolean }>(arg1, arg2);
        return toolResult({
          ok: true,
          skipped: true,
          reason: "rtc_search_code performs candidate indexing automatically",
          workspace_root: workspaceRoot(config, params.path),
          force: Boolean(params.force),
          next_step: "Call rtc_search_code with a focused query.",
        });
      },
    },
    ["rtc_index_codebase"],
  );

  register(
    {
      name: "rtc_search_code",
      label: "RTC Search Code",
      description:
        "Search source code with Retrieval Token Cutter. Use this before broad file reads or source edits.",
      parameters: {
        type: "object",
        additionalProperties: false,
        properties: {
          query: { type: "string", description: "Natural language, symbol, or keyword query." },
          path: { type: "string", description: "Workspace root. Leave empty for the configured workspace." },
          limit: { type: "number", minimum: 1, maximum: 100, description: "Max hits." },
          glob_patterns: { type: "string", description: "Optional comma-separated glob patterns." },
          grep_terms: { type: "string", description: "Optional comma-separated grep terms." },
        },
        required: ["query"],
      },
      async execute(arg1: unknown, arg2: unknown) {
        await ensureBackend?.();
        const params = paramsFromArgs<{
        query: string;
        path?: string;
        limit?: number;
        glob_patterns?: string;
        grep_terms?: string;
        }>(arg1, arg2);
        const body = {
          ...identityFields(config.sessionId),
          accountId: config.accountId,
          userId: config.userId,
          agentId: config.agentId,
          workspaceRoot: workspaceRoot(config, params.path),
          query: canonicalCodeQuery(params.query),
          limit: params.limit ?? config.searchLimit,
          glob_patterns: params.glob_patterns || null,
          grep_terms: params.grep_terms || null,
          waitForFullWorkspaceIndex: false,
        };
        return toolResult(await postJson(config, "/api/v1/call/code_semantic_search", body, 60000));
      },
    },
    ["rtc_search_code"],
  );

  register(
    {
      name: "rtc_edit_file",
      label: "RTC Edit File",
      description:
        "Edit a file through exact string replacement. Use after locating the target with rtc_search_code.",
      parameters: {
        type: "object",
        additionalProperties: false,
        properties: {
          file_path: { type: "string", description: "Absolute or workspace-relative file path." },
          old_string: { type: "string", description: "Exact text to replace." },
          new_string: { type: "string", description: "Replacement text." },
          workspace_root: { type: "string", description: "Workspace root. Leave empty for the configured workspace." },
          replace_all: { type: "boolean", description: "Replace every occurrence." },
        },
        required: ["file_path", "old_string", "new_string"],
      },
      async execute(arg1: unknown, arg2: unknown) {
        await ensureBackend?.();
        const params = paramsFromArgs<{
        file_path: string;
        old_string: string;
        new_string: string;
        workspace_root?: string;
        replace_all?: boolean;
        }>(arg1, arg2);
        const root = workspaceRoot(config, params.workspace_root);
        const target = resolveInside(root, params.file_path);
        const original = await fs.readFile(target, "utf8");
        if (!original.includes(params.old_string)) {
          throw new Error("old_string not found in target file");
        }

        const occurrences = original.split(params.old_string).length - 1;
        if (!params.replace_all && occurrences !== 1) {
          throw new Error(
            `old_string matched ${occurrences} times; pass replace_all=true or provide a more specific old_string`,
          );
        }

        const updated = params.replace_all
          ? original.split(params.old_string).join(params.new_string)
          : original.replace(params.old_string, params.new_string);
        await fs.writeFile(target, updated, "utf8");

        let refresh: unknown;
        try {
          refresh = await postJson(
            config,
            "/api/v1/call/code_refresh_workspace_path",
            {
              ...identityFields(config.sessionId),
              accountId: config.accountId,
              userId: config.userId,
              agentId: config.agentId,
              workspaceRoot: root,
              file_path: target,
              wait_for_index: ["1", "true", "yes", "on"].includes((process.env.RTC_EDIT_REFRESH_WAIT || "0").toLowerCase()),
              refresh_timeout_sec: Number(process.env.RTC_EDIT_REFRESH_TIMEOUT_SEC || "5"),
            },
            8000,
          );
        } catch (error) {
          refresh = { ok: false, background_refresh_dispatched: false, error: String(error) };
        }

        return toolResult({
          ok: true,
          file_path: target,
          relative_path: path.relative(root, target),
          replace_all: Boolean(params.replace_all),
          occurrences,
          bytes_before: Buffer.byteLength(original, "utf8"),
          bytes_after: Buffer.byteLength(updated, "utf8"),
          memory_refresh: refresh,
        });
      },
    },
    ["rtc_edit_file"],
  );
}
