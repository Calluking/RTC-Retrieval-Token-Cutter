import os from "node:os";
import path from "node:path";

export interface RtcPluginConfig {
  repoRoot?: string;
  workspaceRoot?: string;
  rtcUrl?: string;
  runtimeDir?: string;
  autoStart?: boolean;
  autoStop?: boolean;
  startWaitSeconds?: number;
  injectCodePolicy?: boolean;
  readToolPolicy?: string;
  searchLimit?: number;
  accountId?: string;
  userId?: string;
  agentId?: string;
  sessionId?: string;
}

export interface ResolvedConfig {
  pluginRoot: string;
  repoRoot: string;
  workspaceRoot: string;
  rtcUrl: string;
  runtimeDir: string;
  autoStart: boolean;
  autoStop: boolean;
  startWaitSeconds: number;
  injectCodePolicy: boolean;
  readToolPolicy: string;
  searchLimit: number;
  accountId: string;
  userId: string;
  agentId: string;
  sessionId?: string;
}

function expandHome(value: string): string {
  if (value === "~") return os.homedir();
  if (value.startsWith("~/")) return path.join(os.homedir(), value.slice(2));
  return value;
}

export function resolvePathValue(value: string, base = process.cwd()): string {
  const expanded = expandHome(value);
  return path.resolve(base, expanded);
}

function asBoolean(value: unknown, fallback: boolean): boolean {
  if (typeof value === "boolean") return value;
  if (typeof value === "string") {
    return ["1", "true", "yes", "on"].includes(value.toLowerCase());
  }
  return fallback;
}

function asNumber(value: unknown, fallback: number, min: number, max: number): number {
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(min, Math.min(max, Math.trunc(parsed)));
}

function asReadToolPolicy(value: unknown): string {
  const raw = typeof value === "string" ? value.toLowerCase().trim() : "";
  if (["off", "none", "disabled", "disable"].includes(raw)) return "off";
  if (["guard", "strict", "block"].includes(raw)) return "guard";
  if (["advisory", "describe", "description", "warn"].includes(raw)) return "advisory";
  return "advisory";
}

export function resolveWorkspaceRoot(config: RtcPluginConfig): string {
  const raw =
    config.workspaceRoot ||
    process.env.RTC_WORKSPACE_ROOT ||
    process.env.OPENCLAW_WORKSPACE_ROOT ||
    process.env.PWD ||
    process.cwd();
  return resolvePathValue(raw);
}

export function resolveConfig(config: RtcPluginConfig, pluginRoot: string, repoRoot: string): ResolvedConfig {
  const rtcUrl = (config.rtcUrl || process.env.RTC_URL || "http://127.0.0.1:8090").replace(/\/+$/, "");
  const runtimeDir = resolvePathValue(
    config.runtimeDir ||
      process.env.RTC_RUNTIME_DIR ||
      path.join(os.homedir(), ".cache", "retrieval-token-cutter-openclaw-plugin"),
  );

  return {
    pluginRoot,
    repoRoot,
    workspaceRoot: resolveWorkspaceRoot(config),
    rtcUrl,
    runtimeDir,
    autoStart: asBoolean(config.autoStart ?? process.env.RTC_OPENCLAW_AUTO_START, false),
    autoStop: asBoolean(config.autoStop ?? process.env.RTC_OPENCLAW_AUTO_STOP, false),
    startWaitSeconds: asNumber(config.startWaitSeconds ?? process.env.RTC_PLUGIN_START_WAIT, 45, 1, 180),
    injectCodePolicy: asBoolean(config.injectCodePolicy, true),
    readToolPolicy: asReadToolPolicy(config.readToolPolicy ?? process.env.RTC_OPENCLAW_READ_TOOL_POLICY),
    searchLimit: asNumber(config.searchLimit ?? process.env.RTC_SEARCH_LIMIT, 5, 1, 100),
    accountId: config.accountId || process.env.RTC_ACCOUNT_ID || "acct-demo",
    userId: config.userId || process.env.RTC_USER_ID || "u-openclaw",
    agentId: config.agentId || process.env.RTC_AGENT_ID || "openclaw",
    sessionId: config.sessionId || process.env.RTC_SESSION_ID,
  };
}
