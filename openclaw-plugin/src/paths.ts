import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export function currentPluginRoot(importMetaUrl: string): string {
  const file = fileURLToPath(importMetaUrl);
  let dir = path.dirname(file);
  if (path.basename(dir) === "src" || path.basename(dir) === "dist") {
    dir = path.dirname(dir);
  }
  return dir;
}

export function findRepoRoot(pluginRoot: string, configured?: string): string {
  const candidates = [];
  if (configured) candidates.push(path.resolve(configured));
  if (process.env.RTC_SOURCE_TREE) candidates.push(path.resolve(process.env.RTC_SOURCE_TREE));
  candidates.push(path.dirname(pluginRoot));
  candidates.push(process.cwd());

  for (const start of candidates) {
    let cursor = start;
    for (;;) {
      if (
        fs.existsSync(path.join(cursor, "claude-plugin", "scripts", "rtc_terminal.py")) &&
        fs.existsSync(path.join(cursor, "server", "app.py"))
      ) {
        return cursor;
      }
      const parent = path.dirname(cursor);
      if (parent === cursor) break;
      cursor = parent;
    }
  }

  return path.dirname(pluginRoot);
}

export function resolveInside(root: string, filePath: string): string {
  const target = path.resolve(root, filePath);
  const relative = path.relative(root, target);
  if (relative.startsWith("..") || path.isAbsolute(relative)) {
    throw new Error(`Path is outside workspace root: ${filePath}`);
  }
  return target;
}
