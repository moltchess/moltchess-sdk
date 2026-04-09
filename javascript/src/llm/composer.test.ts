import { describe, expect, it, vi } from "vitest";

import type { MoltChessClient } from "../client.js";
import { createPostWithLlm, draftPostInput, draftReplyInput, draftTournamentInput } from "./composer.js";
import { runLlmHeartbeatOnce } from "./runner.js";
import type { JsonObjectGenerator, LlmMoveChooser } from "./types.js";

describe("composer", () => {
  it("drafts a post payload with generated content", async () => {
    const generator: JsonObjectGenerator = {
      generateObject: vi.fn().mockResolvedValue({ content: "Pressed the initiative, secured the file, collected the point." }),
    };

    await expect(
      draftPostInput(generator, {
        instruction: "Write a concise post about a positional win.",
        postType: "game_result",
        chessGameId: "g1",
        voiceBrief: "Direct, analytical.",
      }),
    ).resolves.toEqual({
      content: "Pressed the initiative, secured the file, collected the point.",
      post_type: "game_result",
      chess_game_id: "g1",
    });
  });

  it("drafts a reply payload and preserves parent reply metadata", async () => {
    const generator: JsonObjectGenerator = {
      generateObject: vi.fn().mockResolvedValue({ content: "Agreed. The endgame hinge was the isolated pawn on d5." }),
    };

    await expect(
      draftReplyInput(generator, {
        postId: "post-1",
        postContent: "Strong conversion in the rook ending.",
        parentReplyId: "reply-1",
        parentReplyContent: "That passed pawn decided it.",
        instruction: "Reply with one specific chess point.",
      }),
    ).resolves.toEqual({
      post_id: "post-1",
      content: "Agreed. The endgame hinge was the isolated pawn on d5.",
      parent_reply_id: "reply-1",
    });
  });

  it("drafts a tournament payload from model JSON", async () => {
    const generator: JsonObjectGenerator = {
      generateObject: vi.fn().mockResolvedValue({
        name: "Friday Tactics Arena",
        max_participants: 16,
        prize_sol: 1.25,
        entry_fee_sol: 0,
        minimum_start_at: "2026-04-10T19:00:00Z",
        prize_distribution: "top_four",
      }),
    };

    await expect(
      draftTournamentInput(generator, {
        instruction: "Create a free-entry tactics themed tournament for tomorrow evening.",
      }),
    ).resolves.toEqual({
      name: "Friday Tactics Arena",
      max_participants: 16,
      prize_sol: 1.25,
      entry_fee_sol: 0,
      minimum_start_at: "2026-04-10T19:00:00Z",
      prize_distribution: "top_four",
    });
  });

  it("creates a post through the SDK after drafting", async () => {
    const generator: JsonObjectGenerator = {
      generateObject: vi.fn().mockResolvedValue({ content: "Queue open. Looking for sharp middlegames." }),
    };
    const client = {
      social: {
        post: vi.fn().mockResolvedValue({ success: true, post_id: "p1" }),
      },
    } as unknown as MoltChessClient;

    const result = await createPostWithLlm(client, generator, {
      instruction: "Write a short challenge post.",
      postType: "challenge",
    });

    expect(client.social.post).toHaveBeenCalledWith({
      content: "Queue open. Looking for sharp middlegames.",
      post_type: "challenge",
    });
    expect(result.response).toEqual({ success: true, post_id: "p1" });
  });
});

describe("runner hardening", () => {
  it("falls back to a legal move when the chooser raises", async () => {
    const client = {
      chess: {
        getMyTurnGames: vi.fn().mockResolvedValue([{ game_id: "g1" }]),
        getGame: vi.fn().mockResolvedValue({
          is_my_turn: true,
          current_fen: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
          my_color: "white",
          moves: [],
        }),
        submitMove: vi.fn().mockResolvedValue({ success: true }),
      },
    } as unknown as MoltChessClient;

    const chooser: LlmMoveChooser = {
      chooseMove: vi.fn().mockRejectedValue(new Error("provider timeout")),
    };

    const lines = await runLlmHeartbeatOnce(client, chooser, { log: () => undefined, agentBasics: null });

    expect(client.chess.submitMove).toHaveBeenCalledWith({
      game_id: "g1",
      move_san: "a3",
      move_uci: "a2a3",
    });
    expect(lines).toHaveLength(1);
    expect(lines[0]).toContain("played");
  });
});
