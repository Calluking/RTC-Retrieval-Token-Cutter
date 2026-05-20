import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import type { ResolvedConfig } from "./config.ts";
import { getJson } from "./http.ts";

export class RtcService {
  private startedByPlugin = false;
  private startPromise: Promise<void> | null = null;

  constructor(private readonly config: ResolvedConfig, private readonly logger: { info?: (...args: unknown[]) => void; warn?: (...args: unknown[]) => void }) {}

  async healthy(): Promise<boolean> {
    try {
      await getJson(this.config, "/api/v1/health", 2000);
      return true;
    } catch {
      return false;
    }
  }

  async start(): Promise<void> {
    if (this.startPromise) return this.startPromise;
    this.startPromise = this.startOnce().finally(() => {
      this.startPromise = null;
    });
    return this.startPromise;
  }

  private async startOnce(): Promise<void> {
    if (!this.config.autoStart) return;
    if (await this.healthy()) {
      this.logger.info?.("retrieval-token-cutter: backend already healthy");
      return;
    }

    const script = path.join(this.config.repoRoot, "claude-plugin", "scripts", "rtc_terminal.py");
    if (!fs.existsSync(script)) {
      throw new Error(`RTC service script not found: ${script}`);
    }

    const pyBin = this.pythonBin();
    const env = {
      ...process.env,
      RTC_URL: this.config.rtcUrl,
      RTC_RUNTIME_DIR: this.config.runtimeDir,
      RTC_WORKSPACE_ROOT: this.config.workspaceRoot,
      NO_PROXY: ["127.0.0.1", "localhost", "::1", process.env.NO_PROXY].filter(Boolean).join(","),
      no_proxy: ["127.0.0.1", "localhost", "::1", process.env.no_proxy].filter(Boolean).join(","),
    };

    await new Promise<void>((resolve, reject) => {
      const child = spawn(pyBin, [script, "start", "--runtime-dir", this.config.runtimeDir, "--wait", String(this.config.startWaitSeconds)], {
        cwd: this.config.repoRoot,
        env,
        stdio: ["ignore", "pipe", "pipe"],
      });
      let stderr = "";
      child.stderr.on("data", (chunk) => {
        stderr += String(chunk);
      });
      child.stdout.on("data", (chunk) => {
        this.logger.info?.(String(chunk).trim());
      });
      child.on("error", reject);
      child.on("close", (code) => {
        if (code === 0) {
          this.startedByPlugin = true;
          resolve();
        } else {
          reject(new Error(`RTC service start failed with code ${code}: ${stderr.trim()}`));
        }
      });
    });
  }

  async stop(): Promise<void> {
    if (!this.startedByPlugin || !this.config.autoStop) return;
    const script = path.join(this.config.repoRoot, "claude-plugin", "scripts", "rtc_terminal.py");
    const pyBin = this.pythonBin();
    await new Promise<void>((resolve) => {
      const child = spawn(pyBin, [script, "stop", "--runtime-dir", this.config.runtimeDir], {
        cwd: this.config.repoRoot,
        env: process.env,
        stdio: "ignore",
      });
      child.on("close", () => resolve());
      child.on("error", () => resolve());
      setTimeout(resolve, 10000).unref();
    });
  }

  private pythonBin(): string {
    const candidates = [
      process.env.PY_BIN,
      path.join(this.config.repoRoot, ".venv", "bin", "python"),
      path.join(this.config.repoRoot, ".venv", "bin", "python3"),
      "python3",
      "python",
    ].filter((candidate): candidate is string => Boolean(candidate));

    for (const candidate of candidates) {
      if (this.pythonHasRuntimeDeps(candidate)) return candidate;
    }

    throw new Error(
      [
        "No Python interpreter with Retrieval Token Cutter runtime dependencies was found.",
        `Install them with: cd ${this.config.repoRoot} && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`,
        "Or set PY_BIN=/path/to/python before starting OpenClaw.",
      ].join(" "),
    );
  }

  private pythonHasRuntimeDeps(candidate: string): boolean {
    if (candidate.includes(path.sep) && !fs.existsSync(candidate)) return false;
    const result = spawnSync(
      candidate,
      [
        "-c",
        "import flask\nimport mcp\nimport openai\nimport pyagfs\n",
      ],
      { stdio: "ignore" },
    );
    return result.status === 0;
  }
}
