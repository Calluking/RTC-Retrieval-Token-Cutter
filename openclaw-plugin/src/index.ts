import { definePluginEntry } from "openclaw/plugin-sdk/core";
import type { RtcPluginConfig } from "./config.ts";
import { resolveConfig } from "./config.ts";
import { findRepoRoot, currentPluginRoot } from "./paths.ts";
import { registerPolicyHook } from "./policy.ts";
import { RtcService } from "./rtc-service.ts";
import { registerRtcTools } from "./tools.ts";

export default definePluginEntry({
  id: "retrieval-token-cutter",
  name: "Retrieval Token Cutter",
  description: "Code search and exact-replacement edits backed by Retrieval Token Cutter.",
  register(api: any) {
    const pluginRoot = currentPluginRoot(import.meta.url);
    const pluginConfig = (api.pluginConfig ?? {}) as RtcPluginConfig;
    const repoRoot = findRepoRoot(pluginRoot, pluginConfig.repoRoot);
    const config = resolveConfig(pluginConfig, pluginRoot, repoRoot);
    const service = new RtcService(config, api.logger ?? console);

    api.registerService?.({
      id: "retrieval-token-cutter",
      start: () => service.start(),
      stop: () => service.stop(),
    });

    registerRtcTools(api, config, () => service.start());
    registerPolicyHook(api, config);

    api.logger?.info?.(
      `retrieval-token-cutter: registered tools for workspace ${config.workspaceRoot} using ${config.rtcUrl}`,
    );
  },
});
