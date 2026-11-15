// opencode plugin for local-ai. Keeps one local model in memory at a time (two 27B models
// at once run a 48 GB Mac's GPU out of memory), adds the models the servers report to the
// "local" and "ollama" providers, and gives the agent a local_ai_status tool.
// Load it from opencode.json: "plugin": ["file:///path/to/local-ai/opencode-plugin"]
import { execFile } from "node:child_process"
import { homedir } from "node:os"
import { join } from "node:path"
import { promisify } from "node:util"

const LLAMA_URL = process.env.LOCAL_AI_URL ?? "http://127.0.0.1:8090"
const OLLAMA_URL = process.env.OLLAMA_URL ?? "http://127.0.0.1:11434"
const LLAMA_PROVIDER = process.env.LOCAL_AI_PROVIDER ?? "local"
const OLLAMA_PROVIDER = process.env.LOCAL_AI_OLLAMA_PROVIDER ?? "ollama"
const NEW_MODEL = { reasoning: true, tool_call: true, temperature: true, limit: { context: 131072, output: 8192 } }
const EFFORTS = { low: { reasoningEffort: "low" }, medium: { reasoningEffort: "medium" }, high: { reasoningEffort: "high" } }

async function request(url, body) {
  try {
    const response = await fetch(url, {
      method: body ? "POST" : "GET",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(body ? 30_000 : 2_000),
    })
    if (!response.ok) return null
    const text = await response.text()
    return text ? JSON.parse(text) : {}
  } catch {
    return null
  }
}

async function llamaModels() {
  return (await request(`${LLAMA_URL}/models`))?.data ?? []
}

async function ollamaLoaded() {
  return ((await request(`${OLLAMA_URL}/api/ps`))?.models ?? []).map((model) => model.name)
}

const isLoaded = (model) => ["loaded", "loading"].includes(model.status?.value)
const isEmbedding = (name) => name.includes("embed")

// Unload every chat model on both engines except the one about to answer.
async function makeRoom(providerID, modelID) {
  const unloaded = []
  for (const model of (await llamaModels()).filter(isLoaded)) {
    if (providerID === LLAMA_PROVIDER && model.id === modelID) continue
    if (await request(`${LLAMA_URL}/models/unload`, { model: model.id })) unloaded.push(`llama.cpp ${model.id}`)
  }
  for (const name of await ollamaLoaded()) {
    if ((providerID === OLLAMA_PROVIDER && name === modelID) || isEmbedding(name)) continue
    if (await request(`${OLLAMA_URL}/api/generate`, { model: name, keep_alive: 0 })) unloaded.push(`Ollama ${name}`)
  }
  // Both engines unload in the background; wait until the memory is free before the next
  // model loads, so the two never overlap.
  const gone = async () =>
    !(await llamaModels()).some((model) => isLoaded(model) && unloaded.includes(`llama.cpp ${model.id}`)) &&
    !(await ollamaLoaded()).some((name) => unloaded.includes(`Ollama ${name}`))
  for (let waited = 0; unloaded.length && waited < 15_000 && !(await gone()); waited += 250) {
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  return unloaded
}

async function addServerModels(config) {
  const llama = config.provider?.[LLAMA_PROVIDER]
  if (llama) {
    llama.models ??= {}
    for (const model of await llamaModels()) {
      llama.models[model.id] ??= { name: model.id, ...structuredClone(NEW_MODEL) }
    }
  }
  const ollama = config.provider?.[OLLAMA_PROVIDER]
  if (ollama) {
    ollama.models ??= {}
    for (const model of (await request(`${OLLAMA_URL}/api/tags`))?.models ?? []) {
      if (isEmbedding(model.name)) continue
      ollama.models[model.name] ??= { name: model.name, ...structuredClone(NEW_MODEL), variants: structuredClone(EFFORTS) }
    }
  }
}

async function status() {
  const llama = await llamaModels()
  const lines = [
    `llama.cpp (${LLAMA_URL}): ${llama.length ? llama.map((model) => `${model.id} ${model.status?.value ?? "?"}`).join(", ") : "not reachable"}`,
    `Ollama (${OLLAMA_URL}) loaded: ${(await ollamaLoaded()).join(", ") || "none"}`,
  ]
  try {
    const { stdout } = await promisify(execFile)(join(homedir(), ".local/bin/local-ai-logs"), ["-e"])
    lines.push("", "Latest local-ai-server events and errors:", ...stdout.trimEnd().split("\n").slice(-40))
  } catch {
    lines.push("", "local-ai-logs found no logs")
  }
  return lines.join("\n")
}

export const LocalAI = async ({ client }) => {
  const log = async (message) => {
    try {
      await client.app.log({ body: { service: "local-ai", level: "info", message } })
    } catch {}
  }
  return {
    config: addServerModels,
    "chat.params": async (input) => {
      const providerID = input.model?.providerID ?? input.provider?.info?.id
      if (providerID !== LLAMA_PROVIDER && providerID !== OLLAMA_PROVIDER) return
      const modelID = input.model?.id ?? input.model?.modelID
      const unloaded = await makeRoom(providerID, modelID)
      if (unloaded.length) await log(`unloaded ${unloaded.join(", ")} before ${providerID}/${modelID}`)
    },
    tool: {
      local_ai_status: {
        description:
          "Show which local models are loaded (llama.cpp router and Ollama) and the latest local-ai-server events and errors. Use it when the user asks about the local model server, its state or its logs.",
        args: {},
        execute: status,
      },
    },
  }
}
