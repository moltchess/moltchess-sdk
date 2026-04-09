import { OpenAiJsonGenerator, OpenAiMoveChooser, type OpenAiGeneratorOptions } from "./openai.js";

export const XAI_DEFAULT_BASE = "https://api.x.ai/v1";

export function createGrokJsonGenerator(options: OpenAiGeneratorOptions = {}): OpenAiJsonGenerator {
  return new OpenAiJsonGenerator({
    model: options.model ?? "grok-4",
    apiKey: options.apiKey,
    baseURL: XAI_DEFAULT_BASE,
    timeoutMs: options.timeoutMs,
    maxRetries: options.maxRetries,
  });
}

export function createGrokMoveChooser(options: OpenAiGeneratorOptions = {}): OpenAiMoveChooser {
  return new OpenAiMoveChooser({
    model: options.model ?? "grok-4",
    apiKey: options.apiKey,
    baseURL: XAI_DEFAULT_BASE,
    timeoutMs: options.timeoutMs,
    maxRetries: options.maxRetries,
    maxConversationTurns: options.maxConversationTurns,
    maxGameContexts: options.maxGameContexts,
    gameContextTtlMs: options.gameContextTtlMs,
  });
}
