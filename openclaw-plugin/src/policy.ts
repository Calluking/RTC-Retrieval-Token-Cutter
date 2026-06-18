import fs from "node:fs";
import path from "node:path";
import type { ResolvedConfig } from "./config.ts";
import { identityFields, postJson } from "./http.ts";

const CODE_WORDS = [
  "bug",
  "fix",
  "test",
  "function",
  "class",
  "method",
  "source",
  "code",
  "repo",
  "implementation",
  "traceback",
  "error",
];

const FILTERING_PROMPT_HEADING = "## Filtering Strategy";
const FILTERING_PROMPT_END_MARKER = "Keep the workflow compact:";
const FILTERING_PROMPT_BULLETS = [
  "- Native `read` on long logs/traces may be filtered through RTC before content is returned. The backend stores L0 as filtered content, L1 as properties, and L2 as the original output.",
];

const CAVEMAN_MAX_LEVEL = 3;

function truthyEnv(name: string, fallback = "0"): boolean {
  const raw = (process.env[name] || fallback).trim().toLowerCase();
  return ["1", "true", "yes", "on"].includes(raw);
}

function boolEnv(name: string, fallback = true): boolean {
  const raw = (process.env[name] || "").trim().toLowerCase();
  if (!raw) return fallback;
  return ["1", "true", "yes", "on"].includes(raw);
}

function numberEnv(name: string, fallback: number, min: number, max: number): number {
  const parsed = Number(process.env[name] || fallback);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(min, Math.min(max, Math.trunc(parsed)));
}

export function renderPolicyPrompt(text: string, includeFiltering = truthyEnv("RTC_INJECT_FILTERING_PROMPT", "0")): string {
  if (includeFiltering) return text.trim();

  let rendered = text;
  for (const bullet of FILTERING_PROMPT_BULLETS) {
    rendered = rendered.replace(`${bullet}\n`, "");
  }

  const start = rendered.indexOf(FILTERING_PROMPT_HEADING);
  if (start === -1) return rendered.trim();

  const end = rendered.indexOf(FILTERING_PROMPT_END_MARKER, start);
  if (end === -1) return rendered.slice(0, start).trimEnd();

  return `${rendered.slice(0, start).trimEnd()}\n\n${rendered.slice(end).trimStart()}`.trim();
}

export function cavemanLevel(): number {
  return numberEnv("RTC_CAVEMAN_LEVEL", 0, 0, CAVEMAN_MAX_LEVEL);
}

export function parseCavemanBlock(text: string, level: number): string {
  const startMarker = `### CAVEMAN L${level} ###`;
  const collected: string[] = [];
  let capturing = false;
  for (const line of text.split("\n")) {
    if (line.startsWith("### CAVEMAN")) {
      if (capturing) break;
      if (line.trim() === startMarker) capturing = true;
      continue;
    }
    if (capturing) collected.push(line);
  }
  return collected.join("\n").trim();
}

export function loadCavemanPrompt(pluginRoot: string): string {
  const level = cavemanLevel();
  if (level <= 0) return "";
  const cavemanPath = path.join(pluginRoot, "prompts", "caveman_injection.txt");
  try {
    return parseCavemanBlock(fs.readFileSync(cavemanPath, "utf8"), level);
  } catch {
    return "";
  }
}

function looksLikeCodePrompt(value: string): boolean {
  const lowered = value.toLowerCase();
  return CODE_WORDS.some((word) => lowered.includes(word));
}

function extractPrompt(event: any): string {
  if (!event || typeof event !== "object") return "";
  if (typeof event.prompt === "string") return event.prompt;
  if (typeof event.input === "string") return event.input;
  if (typeof event.userPrompt === "string") return event.userPrompt;
  const messages = Array.isArray(event.messages) ? event.messages : [];
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const message = messages[i];
    if (message?.role !== "user") continue;
    if (typeof message.content === "string") return message.content;
    if (Array.isArray(message.content)) {
      return message.content
        .filter((part: any) => part?.type === "text")
        .map((part: any) => String(part.text || ""))
        .join("\n");
    }
  }
  return "";
}

async function syncWorkspaceOnPrompt(api: any, config: ResolvedConfig, ensureBackend?: () => Promise<void>): Promise<void> {
  if (!boolEnv("RTC_CODE_SYNC_ON_PROMPT", true)) return;
  try {
    await ensureBackend?.();
    const data = await postJson(
      config,
      "/api/v1/call/code_sync_workspace",
      {
        ...identityFields(config.sessionId),
        accountId: config.accountId,
        userId: config.userId,
        agentId: config.agentId,
        workspaceRoot: config.workspaceRoot,
        reason: "before_prompt_build",
        wait_for_index: boolEnv("RTC_CODE_SYNC_WAIT_FOR_INDEX", true),
      },
      numberEnv("RTC_CODE_SYNC_HOOK_TIMEOUT_MS", 30000, 1000, 180000),
    );
    const result = data && typeof data === "object" && !Array.isArray(data) ? data as Record<string, unknown> : {};
    if (result.ok) {
      const apply = result.apply && typeof result.apply === "object" ? result.apply as Record<string, unknown> : {};
      api.logger?.info?.(
        `retrieval-token-cutter: code sync mode=${String(result.mode || "")} changed=${String(result.changed_count || 0)} deleted=${String(result.deleted_count || 0)} ingested=${String(apply.ingested_count || 0)}`,
      );
    } else {
      api.logger?.warn?.(`retrieval-token-cutter: code sync skipped/failed: ${JSON.stringify(result).slice(0, 800)}`);
    }
  } catch (error) {
    api.logger?.warn?.(`retrieval-token-cutter: code sync failed: ${String(error)}`);
  }
}

export function registerPolicyHook(api: any, config: ResolvedConfig, ensureBackend?: () => Promise<void>): void {
  if (typeof api.on !== "function") return;
  const promptPath = path.join(config.pluginRoot, "prompts", "code_policy_injection.txt");
  let policy = "";
  if (config.injectCodePolicy) {
    try {
      policy = renderPolicyPrompt(fs.readFileSync(promptPath, "utf8"));
    } catch (error) {
      api.logger?.warn?.(`retrieval-token-cutter: failed to read policy prompt: ${String(error)}`);
    }
  }

  const caveman = loadCavemanPrompt(config.pluginRoot);

  api.on("before_prompt_build", async (event: any) => {
    const prompt = extractPrompt(event);
    if (!prompt || prompt.startsWith("/")) return event;
    await syncWorkspaceOnPrompt(api, config, ensureBackend);

    const blocks: string[] = [];
    if (config.injectCodePolicy && policy && looksLikeCodePrompt(prompt)) {
      blocks.push(`[Retrieval Token Cutter]\n${policy}`);
    }
    if (caveman) {
      blocks.push(`[Retrieval Token Cutter | Caveman]\n${caveman}`);
    }
    if (blocks.length === 0) return event;

    const context = blocks.join("\n\n");
    return {
      ...event,
      injectedContext: event?.injectedContext ? `${event.injectedContext}\n\n${context}` : context,
      prependContext: event?.prependContext ? `${event.prependContext}\n\n${context}` : context,
    };
  });
}
