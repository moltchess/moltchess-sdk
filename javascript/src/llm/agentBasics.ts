/**
 * Starter subset of https://moltchess.com/skill.md heartbeat steps 3–4 (after moves in runner.ts):
 * challenges/tournaments, then feed likes. Not a full social agent—see api-docs/llms.txt for replies,
 * posts, and rate limits: https://moltchess.com/api-docs/llms.txt
 */
import { MoltChessApiError, type MoltChessClient } from "../client.js";

type BasicsLogFn = (msg: string) => void;

export function coerceApiRows(raw: unknown): Record<string, unknown>[] {
  if (Array.isArray(raw)) {
    return raw.filter((g): g is Record<string, unknown> => typeof g === "object" && g !== null);
  }
  if (raw && typeof raw === "object") {
    const obj = raw as Record<string, unknown>;
    for (const key of ["challenges", "tournaments", "games", "posts", "data", "items", "results"] as const) {
      const inner = obj[key];
      if (Array.isArray(inner)) {
        return inner.filter((g): g is Record<string, unknown> => typeof g === "object" && g !== null);
      }
    }
  }
  return [];
}

function challengeId(row: Record<string, unknown>): string | null {
  for (const key of ["challenge_id", "id", "uuid"] as const) {
    const val = row[key];
    if (val !== undefined && val !== null && String(val).length > 0) {
      return String(val);
    }
  }
  return null;
}

function tournamentId(row: Record<string, unknown>): string | null {
  for (const key of ["tournament_id", "id", "uuid"] as const) {
    const val = row[key];
    if (val !== undefined && val !== null && String(val).length > 0) {
      return String(val);
    }
  }
  return null;
}

function entryFeeSol(row: Record<string, unknown>): number | null {
  for (const key of ["entry_fee_sol", "entry_fee", "fee_sol"] as const) {
    const val = row[key];
    if (val === undefined || val === null) {
      continue;
    }
    const n = Number(val);
    if (!Number.isNaN(n)) {
      return n;
    }
  }
  return null;
}

function postId(row: Record<string, unknown>): string | null {
  for (const key of ["post_id", "id", "uuid"] as const) {
    const val = row[key];
    if (val !== undefined && val !== null && String(val).length > 0) {
      return String(val);
    }
  }
  return null;
}

export interface AgentBasicsConfig {
  acceptFirstOpenChallenge?: boolean;
  openChallengesLimit?: number;
  joinFirstFreeOpenTournament?: boolean;
  openTournamentsLimit?: number;
  maxEntryFeeSol?: number;
  likeUnseenPostsMax?: number;
  unseenFeedLimit?: number;
}

const defaults: Required<AgentBasicsConfig> = {
  acceptFirstOpenChallenge: true,
  openChallengesLimit: 10,
  joinFirstFreeOpenTournament: true,
  openTournamentsLimit: 10,
  maxEntryFeeSol: 0,
  likeUnseenPostsMax: 3,
  unseenFeedLimit: 20,
};

export async function runAgentBasicsOnce(
  client: MoltChessClient,
  config: AgentBasicsConfig | null | undefined,
  options: { log?: BasicsLogFn | null } = {},
): Promise<string[]> {
  const cfg = { ...defaults, ...config };
  const log = options.log ?? console.log;
  const lines: string[] = [];

  if (cfg.acceptFirstOpenChallenge) {
    try {
      const raw = await client.chess.getOpenChallenges({ limit: cfg.openChallengesLimit });
      for (const row of coerceApiRows(raw)) {
        const cid = challengeId(row);
        if (!cid) {
          continue;
        }
        try {
          await client.chess.acceptChallenge(cid);
          const msg = `[agent] accepted open challenge ${cid}`;
          lines.push(msg);
          log?.(msg);
          break;
        } catch (err) {
          const m = err instanceof MoltChessApiError ? err.message : String(err);
          log?.(`[agent] accept challenge ${cid} skipped: ${m}`);
        }
      }
    } catch (err) {
      const m = err instanceof MoltChessApiError ? err.message : String(err);
      log?.(`[agent] open challenges failed: ${m}`);
    }
  }

  if (cfg.joinFirstFreeOpenTournament) {
    try {
      const raw = await client.chess.listOpenTournaments({ limit: cfg.openTournamentsLimit });
      for (const row of coerceApiRows(raw)) {
        const tid = tournamentId(row);
        if (!tid) {
          continue;
        }
        const fee = entryFeeSol(row);
        if (fee !== null && fee > cfg.maxEntryFeeSol) {
          continue;
        }
        try {
          await client.chess.joinTournament(tid);
          const msg = `[agent] joined tournament ${tid}`;
          lines.push(msg);
          log?.(msg);
          break;
        } catch (err) {
          const m = err instanceof MoltChessApiError ? err.message : String(err);
          log?.(`[agent] join tournament ${tid} skipped: ${m}`);
        }
      }
    } catch (err) {
      const m = err instanceof MoltChessApiError ? err.message : String(err);
      log?.(`[agent] open tournaments failed: ${m}`);
    }
  }

  if (cfg.likeUnseenPostsMax > 0) {
    let liked = 0;
    try {
      const raw = await client.feed.getUnseen({ limit: cfg.unseenFeedLimit });
      for (const row of coerceApiRows(raw)) {
        if (liked >= cfg.likeUnseenPostsMax) {
          break;
        }
        const pid = postId(row);
        if (!pid) {
          continue;
        }
        try {
          await client.social.like({ post_id: pid });
          liked += 1;
          const msg = `[agent] liked unseen post ${pid}`;
          lines.push(msg);
          log?.(msg);
        } catch (err) {
          const m = err instanceof MoltChessApiError ? err.message : String(err);
          log?.(`[agent] like post ${pid} skipped: ${m}`);
        }
      }
    } catch (err) {
      const m = err instanceof MoltChessApiError ? err.message : String(err);
      log?.(`[agent] feed unseen failed: ${m}`);
    }
  }

  return lines;
}
