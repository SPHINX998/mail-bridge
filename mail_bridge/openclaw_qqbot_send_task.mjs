import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { pathToFileURL } from "node:url";

async function readStdinJson() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(Buffer.from(chunk));
  }
  const raw = Buffer.concat(chunks).toString("utf8").trim();
  return JSON.parse(raw || "{}");
}

function resolveOpenClawHome(input) {
  if (typeof input.openclawHome === "string" && input.openclawHome.trim()) {
    return input.openclawHome.trim();
  }
  const stateDir = typeof process.env.OPENCLAW_STATE_DIR === "string" ? process.env.OPENCLAW_STATE_DIR.trim() : "";
  if (stateDir) {
    return path.dirname(stateDir);
  }
  return process.env.USERPROFILE || os.homedir();
}

function resolveConfigPath(input, openclawHome) {
  if (typeof input.configFile === "string" && input.configFile.trim()) {
    return input.configFile.trim();
  }
  if (typeof process.env.OPENCLAW_CONFIG_PATH === "string" && process.env.OPENCLAW_CONFIG_PATH.trim()) {
    return process.env.OPENCLAW_CONFIG_PATH.trim();
  }
  return path.join(openclawHome, ".openclaw", "openclaw.json");
}

async function loadJson(filePath) {
  const raw = await fs.readFile(filePath, "utf8");
  return JSON.parse(raw);
}

async function findQQBotPluginRoot(openclawHome) {
  const extensionsDir = path.join(openclawHome, ".openclaw", "extensions");
  const entries = await fs.readdir(extensionsDir, { withFileTypes: true });
  for (const entry of entries) {
    if (!entry.isDirectory()) {
      continue;
    }
    const packageJsonPath = path.join(extensionsDir, entry.name, "package.json");
    try {
      const packageJson = await loadJson(packageJsonPath);
      const packageName = typeof packageJson?.name === "string" ? packageJson.name : "";
      const openclawId = typeof packageJson?.openclaw?.id === "string" ? packageJson.openclaw.id : "";
      if (packageName === "@tencent-connect/openclaw-qqbot" || openclawId === "openclaw-qqbot") {
        return path.join(extensionsDir, entry.name);
      }
    } catch {
      continue;
    }
  }
  throw new Error("找不到 OpenClaw QQ Bot 插件目录");
}

function normalizeResult(result) {
  return {
    channel: typeof result?.channel === "string" ? result.channel : "qqbot",
    messageId: result?.messageId ?? null,
    timestamp: result?.timestamp ?? null,
    error: result?.error ?? null,
  };
}

async function main() {
  const input = await readStdinJson();
  const target = typeof input.target === "string" ? input.target.trim() : "";
  const text = typeof input.text === "string" ? input.text : "";
  if (!target) {
    throw new Error("QQ Bot 目标不能为空");
  }
  if (!text.trim()) {
    throw new Error("QQ Bot 消息内容不能为空");
  }

  const openclawHome = resolveOpenClawHome(input);
  const configPath = resolveConfigPath(input, openclawHome);
  const config = await loadJson(configPath);
  const pluginRoot = await findQQBotPluginRoot(openclawHome);
  const configModule = await import(pathToFileURL(path.join(pluginRoot, "dist", "src", "config.js")).href);
  const apiModule = await import(pathToFileURL(path.join(pluginRoot, "dist", "src", "api.js")).href);
  const outboundModule = await import(pathToFileURL(path.join(pluginRoot, "dist", "src", "outbound.js")).href);

  const accountId =
    typeof input.accountId === "string" && input.accountId.trim() ? input.accountId.trim() : undefined;
  const account = configModule.resolveQQBotAccount(config, accountId);
  if (!account?.appId || !account?.clientSecret) {
    throw new Error("OpenClaw QQ Bot 账号缺少 appId 或 clientSecret");
  }
  apiModule.initApiConfig({ markdownSupport: account.markdownSupport });
  const result = await outboundModule.sendText({
    to: target,
    text,
    replyToId: null,
    accountId: account.accountId,
    account,
  });
  const normalized = normalizeResult(result);
  if (normalized.error) {
    throw new Error(typeof normalized.error === "string" ? normalized.error : String(normalized.error));
  }
  process.stdout.write(JSON.stringify(normalized));
}

main().catch((error) => {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exit(1);
});
