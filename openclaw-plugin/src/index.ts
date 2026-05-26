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

    registerRtcTools(api, config, async () => {
      if (config.autoStart) await service.start();
    });
    registerPolicyHook(api, config);
    if (config.readToolPolicy === "guard" && typeof api.on === "function") {
      api.on("before_tool_call", (event: any) => {
        if (event?.toolName !== "read") return undefined;
        return {
          block: true,
          blockReason:
            "Native read is disabled by Retrieval Token Cutter for this run. Use rtc_search_code for code context, or rtc_read only when RTC search misses the needed exact text after a focused retry.",
        };
      });
      api.on("before_tool_call", (event: any) => {
        if (event?.toolName !== "edit") return undefined;
        return {
          block: true,
          blockReason:
            "Native edit is disabled by Retrieval Token Cutter for this run. Use rtc_edit_file with old_string copied from rtc_search_code content_excerpt or a narrow rtc_read result.",
        };
      });
    }

    api.logger?.info?.(
      `retrieval-token-cutter: registered tools for workspace ${config.workspaceRoot} using ${config.rtcUrl}`,
    );
  },
});
