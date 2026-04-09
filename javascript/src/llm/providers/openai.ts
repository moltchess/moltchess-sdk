import OpenAI from "openai";

import { extractJsonObject, parseMoveChoice } from "../jsonutil.js";
import { SYSTEM_PROMPT, buildUserMessage } from "../prompt.js";
import type { JsonObjectGenerator, LlmMoveChooser, MovePromptContext, ParsedMoveChoice } from "../types.js";

export interface OpenAiGeneratorOptions {
  model?: string;
  apiKey?: string;
  baseURL?: string;
  timeoutMs?: number;
  maxRetries?: number;
  maxConversationTurns?: number;
  maxGameContexts?: number;
  gameContextTtlMs?: number;
}

interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
}

interface GeneratedJsonReply {
  text: string;
  data: Record<string, unknown>;
}

interface GameConversationState {
  messages: ConversationMessage[];
  lastMovesSummary: string | null;
  lastTouchedAt: number;
}

export class OpenAiJsonGenerator implements JsonObjectGenerator {
  protected readonly client: OpenAI;
  protected readonly model: string;

  constructor(options: OpenAiGeneratorOptions = {}) {
    this.client = new OpenAI({
      apiKey: options.apiKey,
      baseURL: options.baseURL,
      timeout: options.timeoutMs,
      maxRetries: options.maxRetries,
    });
    this.model = options.model ?? "gpt-5.4-mini";
  }

  protected async generateReply(
    systemPrompt: string,
    messages: ConversationMessage[],
  ): Promise<GeneratedJsonReply> {
    const completion = await this.client.chat.completions.create({
      model: this.model,
      temperature: 0.2,
      response_format: { type: "json_object" },
      messages: [
        { role: "system", content: systemPrompt },
        ...messages,
      ],
    });
    const text = completion.choices[0]?.message?.content ?? "{}";
    return {
      text,
      data: extractJsonObject(text),
    };
  }

  async generateObject(systemPrompt: string, userMessage: string): Promise<Record<string, unknown>> {
    const reply = await this.generateReply(systemPrompt, [{ role: "user", content: userMessage }]);
    return reply.data;
  }
}

export class OpenAiMoveChooser extends OpenAiJsonGenerator implements LlmMoveChooser {
  private readonly sessions = new Map<string, GameConversationState>();
  private readonly maxConversationTurns: number;
  private readonly maxGameContexts: number;
  private readonly gameContextTtlMs: number;

  constructor(options: OpenAiGeneratorOptions = {}) {
    super(options);
    this.maxConversationTurns = options.maxConversationTurns ?? 6;
    this.maxGameContexts = options.maxGameContexts ?? 256;
    this.gameContextTtlMs = options.gameContextTtlMs ?? 24 * 60 * 60 * 1000;
  }

  async chooseMove(ctx: MovePromptContext, feedback?: string | null): Promise<ParsedMoveChoice> {
    const now = Date.now();
    this.pruneSessions(now);
    const session = this.getSession(ctx.gameId, now);
    const user = buildUserMessage(ctx, {
      previousMovesSummary: session.lastMovesSummary,
      feedback,
    });
    const reply = await this.generateReply(SYSTEM_PROMPT, [...session.messages, { role: "user", content: user }]);
    const choice = parseMoveChoice(reply.data);

    session.messages = this.trimMessages([
      ...session.messages,
      { role: "user", content: user },
      { role: "assistant", content: reply.text },
    ]);
    session.lastMovesSummary = ctx.movesSummary;
    session.lastTouchedAt = Date.now();

    return choice;
  }

  private getSession(gameId: string, now: number): GameConversationState {
    const existing = this.sessions.get(gameId);
    if (existing) {
      existing.lastTouchedAt = now;
      return existing;
    }
    const created: GameConversationState = {
      messages: [],
      lastMovesSummary: null,
      lastTouchedAt: now,
    };
    this.sessions.set(gameId, created);
    this.pruneSessions(now);
    return created;
  }

  private trimMessages(messages: ConversationMessage[]): ConversationMessage[] {
    const maxMessages = Math.max(1, this.maxConversationTurns) * 2;
    if (messages.length <= maxMessages) {
      return messages;
    }
    return messages.slice(messages.length - maxMessages);
  }

  private pruneSessions(now: number): void {
    for (const [gameId, session] of this.sessions) {
      if (now - session.lastTouchedAt > this.gameContextTtlMs) {
        this.sessions.delete(gameId);
      }
    }
    while (this.sessions.size > this.maxGameContexts) {
      let oldestGameId: string | null = null;
      let oldestTouchedAt = Number.POSITIVE_INFINITY;
      for (const [gameId, session] of this.sessions) {
        if (session.lastTouchedAt < oldestTouchedAt) {
          oldestTouchedAt = session.lastTouchedAt;
          oldestGameId = gameId;
        }
      }
      if (!oldestGameId) {
        return;
      }
      this.sessions.delete(oldestGameId);
    }
  }
}
