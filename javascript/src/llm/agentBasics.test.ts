import { describe, expect, it, vi } from "vitest";

import { coerceApiRows, runAgentBasicsOnce } from "./agentBasics.js";
import type { MoltChessClient } from "../client.js";

describe("coerceApiRows", () => {
  it("unwraps challenges", () => {
    const rows = coerceApiRows({ challenges: [{ challenge_id: "a" }] });
    expect(rows).toHaveLength(1);
    expect(rows[0].challenge_id).toBe("a");
  });
});

describe("runAgentBasicsOnce", () => {
  it("accepts, joins, and likes with mock client", async () => {
    const client = {
      chess: {
        getOpenChallenges: vi.fn().mockResolvedValue([{ challenge_id: "c1" }]),
        acceptChallenge: vi.fn().mockResolvedValue({ ok: true }),
        listOpenTournaments: vi.fn().mockResolvedValue([{ tournament_id: "t1", entry_fee_sol: 0 }]),
        joinTournament: vi.fn().mockResolvedValue({ ok: true }),
      },
      feed: {
        getUnseen: vi.fn().mockResolvedValue([{ post_id: "p1" }, { post_id: "p2" }]),
      },
      social: {
        like: vi.fn().mockResolvedValue({ ok: true }),
      },
    } as unknown as MoltChessClient;

    const lines = await runAgentBasicsOnce(client, { likeUnseenPostsMax: 2 }, { log: () => undefined });
    expect(lines.some((l) => l.includes("accepted open challenge"))).toBe(true);
    expect(lines.some((l) => l.includes("joined tournament"))).toBe(true);
    expect(client.social.like).toHaveBeenCalledTimes(2);
  });
});
