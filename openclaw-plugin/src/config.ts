import os from "node:os";
import fs from "node:fs";
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
  filterEnabled?: boolean;
  filterNativeRead?: boolean;
  filterNativeExec?: boolean;
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
  filterEnabled: boolean;
  filterNativeRead: boolean;
  filterNativeExec: boolean;
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

function truthyEnv(name: string): boolean {
  const raw = (process.env[name] || "").trim().toLowerCase();
  return ["1", "true", "yes", "on"].includes(raw);
}

function launchCwd(): string | undefined {
  if (truthyEnv("RTC_OPENCLAW_IGNORE_LAUNCH_CWD")) return undefined;
  const raw = process.env.RTC_OPENCLAW_LAUNCH_CWD || process.env.PWD;
  if (!raw) return undefined;
  const candidate = resolvePathValue(raw);
  try {
    if (fs.statSync(candidate).isDirectory()) return candidate;
  } catch {
    // Ignore stale inherited PWD values and fall back to OpenClaw's cwd.
  }
  return undefined;
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
  const respectConfig = truthyEnv("RTC_OPENCLAW_RESPECT_CONFIG");
  const respectEnvPaths = truthyEnv("RTC_OPENCLAW_RESPECT_ENV_PATHS") || respectConfig;
  const raw =
    (respectEnvPaths ? process.env.RTC_WORKSPACE_ROOT || process.env.OPENCLAW_WORKSPACE_ROOT : undefined) ||
    (respectConfig && truthyEnv("RTC_OPENCLAW_RESPECT_CONFIG_WORKSPACE") ? config.workspaceRoot : undefined) ||
    launchCwd() ||
    process.cwd();
  return resolvePathValue(raw);
}

export function resolveConfig(config: RtcPluginConfig, pluginRoot: string, repoRoot: string): ResolvedConfig {
  const respectConfig = truthyEnv("RTC_OPENCLAW_RESPECT_CONFIG");
  const respectEnvPaths = truthyEnv("RTC_OPENCLAW_RESPECT_ENV_PATHS") || respectConfig;
  const effectiveConfig = respectConfig ? config : {};
  const rtcUrl = (effectiveConfig.rtcUrl || process.env.RTC_URL || "http://127.0.0.1:8090").replace(/\/+$/, "");
  const runtimeDir = resolvePathValue(
    effectiveConfig.runtimeDir ||
      (respectEnvPaths ? process.env.RTC_RUNTIME_DIR : undefined) ||
      path.join(os.homedir(), ".cache", "retrieval-token-cutter-openclaw-plugin"),
  );

  return {
    pluginRoot,
    repoRoot,
    workspaceRoot: resolveWorkspaceRoot(config),
    rtcUrl,
    runtimeDir,
    autoStart: asBoolean(effectiveConfig.autoStart ?? process.env.RTC_OPENCLAW_AUTO_START ?? process.env.RTC_PLUGIN_AUTO_START, true),
    autoStop: asBoolean(effectiveConfig.autoStop ?? process.env.RTC_OPENCLAW_AUTO_STOP ?? process.env.RTC_PLUGIN_AUTO_STOP, true),
    startWaitSeconds: asNumber(effectiveConfig.startWaitSeconds ?? process.env.RTC_PLUGIN_START_WAIT, 45, 1, 180),
    injectCodePolicy: asBoolean(effectiveConfig.injectCodePolicy, true),
    readToolPolicy: asReadToolPolicy(effectiveConfig.readToolPolicy ?? process.env.RTC_OPENCLAW_READ_TOOL_POLICY),
    filterEnabled: asBoolean(effectiveConfig.filterEnabled ?? process.env.RTC_FILTER_ENABLED, true),
    filterNativeRead: asBoolean(effectiveConfig.filterNativeRead ?? process.env.RTC_FILTER_NATIVE_READ, true),
    filterNativeExec: asBoolean(effectiveConfig.filterNativeExec ?? process.env.RTC_FILTER_NATIVE_BASH, true),
    searchLimit: asNumber(effectiveConfig.searchLimit ?? process.env.RTC_SEARCH_LIMIT, 5, 1, 100),
    accountId: effectiveConfig.accountId || process.env.RTC_ACCOUNT_ID || "acct-demo",
    userId: effectiveConfig.userId || process.env.RTC_USER_ID || "u-openclaw",
    agentId: effectiveConfig.agentId || process.env.RTC_AGENT_ID || "openclaw",
    sessionId: effectiveConfig.sessionId || process.env.RTC_SESSION_ID,
  };
}
