import { AnthropicJsonGenerator, AnthropicMoveChooser } from "./providers/anthropic.js";
import { OpenAiJsonGenerator, OpenAiMoveChooser } from "./providers/openai.js";
import { createGrokJsonGenerator, createGrokMoveChooser } from "./providers/grok.js";
import type { JsonObjectGenerator, LlmMoveChooser } from "./types.js";

function providerOptions(env: NodeJS.ProcessEnv = process.env): {
  openai: { model?: string; apiKey?: string; timeoutMs?: number; maxRetries?: number };
  anthropic: { model?: string; apiKey?: string; timeoutMs?: number; maxRetries?: number };
  grok: { model?: string; apiKey?: string; timeoutMs?: number; maxRetries?: number };
} {
  const timeoutMsRaw = env.LLM_TIMEOUT_MS ? Number(env.LLM_TIMEOUT_MS) : 20_000;
  const timeoutMs = Number.isFinite(timeoutMsRaw) && timeoutMsRaw > 0 ? timeoutMsRaw : 20_000;
  const maxRetriesRaw = env.LLM_MAX_RETRIES ? Number(env.LLM_MAX_RETRIES) : 0;
  const maxRetries = Number.isFinite(maxRetriesRaw) && maxRetriesRaw >= 0 ? maxRetriesRaw : 0;
  return {
    openai: {
      model: env.OPENAI_MODEL,
      apiKey: env.OPENAI_API_KEY,
      timeoutMs,
      maxRetries,
    },
    anthropic: {
      model: env.ANTHROPIC_MODEL,
      apiKey: env.ANTHROPIC_API_KEY,
      timeoutMs,
      maxRetries,
    },
    grok: {
      model: env.XAI_MODEL,
      apiKey: env.XAI_API_KEY,
      timeoutMs,
      maxRetries,
    },
  };
}

export function createMoveChooser(provider: string, env: NodeJS.ProcessEnv = process.env): LlmMoveChooser {
  const p = provider.trim().toLowerCase();
  const options = providerOptions(env);
  if (p === "openai") {
    return new OpenAiMoveChooser(options.openai);
  }
  if (p === "anthropic") {
    return new AnthropicMoveChooser(options.anthropic);
  }
  if (p === "grok") {
    return createGrokMoveChooser(options.grok);
  }
  throw new Error(`Unknown LLM provider: ${JSON.stringify(provider)} (use openai, anthropic, grok)`);
}

export function createJsonGenerator(provider: string, env: NodeJS.ProcessEnv = process.env): JsonObjectGenerator {
  const p = provider.trim().toLowerCase();
  const options = providerOptions(env);
  if (p === "openai") {
    return new OpenAiJsonGenerator(options.openai);
  }
  if (p === "anthropic") {
    return new AnthropicJsonGenerator(options.anthropic);
  }
  if (p === "grok") {
    return createGrokJsonGenerator(options.grok);
  }
  throw new Error(`Unknown LLM provider: ${JSON.stringify(provider)} (use openai, anthropic, grok)`);
}
