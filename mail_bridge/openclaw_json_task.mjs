import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { pathToFileURL } from "node:url";

function stripCodeFences(text) {
  const trimmed = String(text ?? "").trim();
  const match = trimmed.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i);
  return match ? String(match[1] ?? "").trim() : trimmed;
}

function collectText(payloads) {
  return (Array.isArray(payloads) ? payloads : [])
    .filter((payload) => !payload?.isError && typeof payload?.text === "string")
    .map((payload) => payload.text)
    .join("\n")
    .trim();
}

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

function resolveOpenClawConfigPath(input, openclawHome) {
  if (typeof input.configFile === "string" && input.configFile.trim()) {
    return input.configFile.trim();
  }
  return path.join(openclawHome, ".openclaw", "openclaw.json");
}

async function loadOpenClawConfig(configFile) {
  const raw = await fs.readFile(configFile, "utf8");
  return JSON.parse(raw);
}

function parseModelRef(value) {
  if (typeof value !== "string" || !value.includes("/")) {
    return null;
  }
  const [provider, ...modelParts] = value.split("/");
  const model = modelParts.join("/");
  if (!provider || !model) {
    return null;
  }
  return { provider, model };
}

function resolveJsonTaskModel(config, agentId) {
  const agentEntry = Array.isArray(config?.agents?.list)
    ? config.agents.list.find((entry) => entry?.id === agentId)
    : null;
  const fallbacks =
    agentEntry?.model && typeof agentEntry.model === "object" && Array.isArray(agentEntry.model.fallbacks)
      ? agentEntry.model.fallbacks
      : [];
  for (const candidate of fallbacks) {
    const parsed = parseModelRef(candidate);
    if (parsed) {
      return parsed;
    }
  }
  const agentPrimary =
    agentEntry?.model && typeof agentEntry.model === "object" ? parseModelRef(agentEntry.model.primary) : null;
  if (agentPrimary) {
    return agentPrimary;
  }
  const defaultsModel = config?.agents?.defaults?.model;
  if (typeof defaultsModel === "string") {
    const parsed = parseModelRef(defaultsModel);
    if (parsed) {
      return parsed;
    }
  }
  if (defaultsModel && typeof defaultsModel === "object") {
    const parsed = parseModelRef(defaultsModel.primary);
    if (parsed) {
      return parsed;
    }
  }
  throw new Error("无法从 OpenClaw 配置解析 JSON task 默认 provider/model");
}

async function loadRunEmbeddedPiAgent() {
  const openclawDist = path.join(
    process.env.APPDATA ?? path.join(os.homedir(), "AppData", "Roaming"),
    "npm",
    "node_modules",
    "openclaw",
    "dist",
    "extensionAPI.js",
  );
  const mod = await import(pathToFileURL(openclawDist).href);
  if (typeof mod.runEmbeddedPiAgent !== "function") {
    throw new Error("OpenClaw internal runner 不可用");
  }
  return mod.runEmbeddedPiAgent;
}

async function main() {
  const input = await readStdinJson();
  const openclawHome = resolveOpenClawHome(input);
  const configPath = resolveOpenClawConfigPath(input, openclawHome);
  const config = await loadOpenClawConfig(configPath);
  const agentId = typeof input.agentId === "string" && input.agentId.trim() ? input.agentId.trim() : "main";
  const { provider: defaultProvider, model: defaultModel } = resolveJsonTaskModel(config, agentId);
  const provider = typeof input.provider === "string" && input.provider.trim() ? input.provider.trim() : defaultProvider;
  const model = typeof input.model === "string" && input.model.trim() ? input.model.trim() : defaultModel;
  const thinkLevel = typeof input.thinking === "string" && input.thinking.trim() ? input.thinking.trim() : undefined;
  const timeoutMs = typeof input.timeoutMs === "number" && input.timeoutMs > 0 ? input.timeoutMs : 30000;
  const sessionId =
    typeof input.sessionId === "string" && input.sessionId.trim()
      ? input.sessionId.trim()
      : `mail-bridge-llm-task-${Date.now()}`;
  const workspaceDir = config?.agents?.defaults?.workspace || process.cwd();
  const taskPrompt = typeof input.prompt === "string" ? input.prompt : "";
  const taskInput = input.input ?? null;
  const explicitSessionFile =
    typeof input.sessionFile === "string" && input.sessionFile.trim() ? path.resolve(input.sessionFile.trim()) : null;
  const fullPrompt = [
    "You are a JSON-only function.",
    "Return ONLY a valid JSON value.",
    "Do not wrap in markdown fences.",
    "Do not include commentary.",
    "Do not call tools.",
    "",
    "TASK:",
    taskPrompt,
    "",
    "INPUT_JSON:",
    JSON.stringify(taskInput, null, 2),
    "",
  ].join("\n");

  const tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "mail-bridge-openclaw-"));
  const sessionFile = explicitSessionFile ?? path.join(tmpDir, "session.jsonl");
  try {
    await fs.mkdir(path.dirname(sessionFile), { recursive: true });
    const runEmbeddedPiAgent = await loadRunEmbeddedPiAgent();
    const result = await runEmbeddedPiAgent({
      sessionId,
      agentId,
      sessionFile,
      workspaceDir,
      config,
      prompt: fullPrompt,
      timeoutMs,
      runId: `mail-bridge-${Date.now()}`,
      provider,
      model,
      thinkLevel,
      reasoningLevel: thinkLevel === "off" ? "off" : undefined,
      verboseLevel: "off",
      disableTools: true,
    });
    const text = collectText(result?.payloads);
    if (!text) {
      throw new Error("OpenClaw JSON task 返回为空");
    }
    const parsed = JSON.parse(stripCodeFences(text));
    process.stdout.write(JSON.stringify(parsed));
  } finally {
    await fs.rm(tmpDir, { recursive: true, force: true }).catch(() => {});
  }
}

main().catch((error) => {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exit(1);
});
