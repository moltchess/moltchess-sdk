import { describe, expect, it } from "vitest";

import { buildUserMessage, summarizeMoveDelta } from "./prompt.js";
import { OpenAiMoveChooser } from "./providers/openai.js";
import type { MovePromptContext } from "./types.js";

class RecordingMoveChooser extends OpenAiMoveChooser {
  readonly calls: Array<Array<{ role: string; content: string }>> = [];
  private readonly replies: string[];

  constructor(replies: string[]) {
    super({ apiKey: "test-key" });
    this.replies = [...replies];
  }

  protected override async generateReply(
    _systemPrompt: string,
    messages: Array<{ role: "user" | "assistant"; content: string }>,
  ): Promise<{ text: string; data: Record<string, unknown> }> {
    this.calls.push(messages.map((message) => ({ role: message.role, content: message.content })));
    const text = this.replies.shift() ?? '{"move_san":"Nf3","move_uci":"g1f3"}';
    return { text, data: JSON.parse(text) as Record<string, unknown> };
  }
}

function makeCtx(overrides: Partial<MovePromptContext> = {}): MovePromptContext {
  return {
    gameId: overrides.gameId ?? "g1",
    fen: overrides.fen ?? "fen",
    myColor: overrides.myColor ?? "white",
    legalSans: overrides.legalSans ?? ["Nf3"],
    legalUci: overrides.legalUci ?? ["g1f3"],
    movesSummary: overrides.movesSummary ?? "e4 e5",
  };
}

describe("prompt", () => {
  it("summarizes append-only move deltas", () => {
    expect(summarizeMoveDelta("e4 e5", "e4 e5 Nf3 Nc6")).toEqual({
      mode: "continue",
      newMoves: ["Nf3", "Nc6"],
    });
  });

  it("builds compact follow-up prompts for ongoing games", () => {
    const text = buildUserMessage(makeCtx({ movesSummary: "e4 e5 Nf3 Nc6" }), {
      previousMovesSummary: "e4 e5",
    });

    expect(text).toContain("Continue the same game thread. Do not repeat prior analysis.");
    expect(text).toContain("New SAN moves since your last prompt: Nf3 Nc6");
    expect(text).not.toContain("Full move history (SAN)");
  });

  it("keeps conversations isolated per game id", async () => {
    const chooser = new RecordingMoveChooser([
      '{"move_san":"Nf3","move_uci":"g1f3"}',
      '{"move_san":"Bc4","move_uci":"f1c4"}',
      '{"move_san":"d4","move_uci":"d2d4"}',
    ]);

    await chooser.chooseMove(makeCtx({ gameId: "g1", movesSummary: "e4 e5" }));
    await chooser.chooseMove(makeCtx({ gameId: "g1", movesSummary: "e4 e5 Nf3 Nc6", legalSans: ["Bc4"], legalUci: ["f1c4"] }));
    await chooser.chooseMove(makeCtx({ gameId: "g2", movesSummary: "d4 d5", legalSans: ["c4"], legalUci: ["c2c4"] }));

    expect(chooser.calls[0]).toHaveLength(1);
    expect(chooser.calls[0][0]?.content).toContain("This is the first prompt for this game thread.");

    expect(chooser.calls[1]).toHaveLength(3);
    expect(chooser.calls[1][2]?.content).toContain("New SAN moves since your last prompt: Nf3 Nc6");
    expect(chooser.calls[1][2]?.content).not.toContain("Full move history (SAN)");

    expect(chooser.calls[2]).toHaveLength(1);
    expect(chooser.calls[2][0]?.content).toContain("game_id: g2");
    expect(chooser.calls[2][0]?.content).toContain("This is the first prompt for this game thread.");
  });
});
