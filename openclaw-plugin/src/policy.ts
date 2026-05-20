import fs from "node:fs";
import path from "node:path";
import type { ResolvedConfig } from "./config.ts";

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

export function registerPolicyHook(api: any, config: ResolvedConfig): void {
  if (!config.injectCodePolicy || typeof api.on !== "function") return;
  const promptPath = path.join(config.pluginRoot, "prompts", "code_policy_injection.txt");
  let policy = "";
  try {
    policy = fs.readFileSync(promptPath, "utf8").trim();
  } catch (error) {
    api.logger?.warn?.(`retrieval-token-cutter: failed to read policy prompt: ${String(error)}`);
    return;
  }

  api.on("before_prompt_build", async (event: any) => {
    const prompt = extractPrompt(event);
    if (!prompt || prompt.startsWith("/") || !looksLikeCodePrompt(prompt)) return event;
    const context = `[Retrieval Token Cutter]\n${policy}`;
    return {
      ...event,
      injectedContext: event?.injectedContext ? `${event.injectedContext}\n\n${context}` : context,
      prependContext: event?.prependContext ? `${event.prependContext}\n\n${context}` : context,
    };
  });
}
