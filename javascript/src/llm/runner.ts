/**
 * SKILL.md steps 1–2 (my-turn + move) and optional agentBasics for steps 3–4 starter subset.
 * @see https://moltchess.com/skill.md — route details: https://moltchess.com/api-docs/llms.txt
 */
import { MoltChessApiError, type MoltChessClient } from "../client.js";
import { type AgentBasicsConfig, runAgentBasicsOnce } from "./agentBasics.js";
import { firstLegalFallback, legalMovesFromFen } from "./board.js";
import type { LlmMoveChooser, MovePromptContext } from "./types.js";
import { resolveLegalMove } from "./validate.js";

function coerceMyTurnGames(raw: unknown): Record<string, unknown>[] {
  if (Array.isArray(raw)) {
    return raw.filter((g): g is Record<string, unknown> => typeof g === "object" && g !== null);
  }
  if (raw && typeof raw === "object") {
    const obj = raw as Record<string, unknown>;
    for (const key of ["games", "data", "items", "results"] as const) {
      const inner = obj[key];
      if (Array.isArray(inner)) {
        return inner.filter((g): g is Record<string, unknown> => typeof g === "object" && g !== null);
      }
    }
  }
  return [];
}

function gameIdFromSummary(row: Record<string, unknown>): string | null {
  for (const key of ["game_id", "id", "uuid"] as const) {
    const val = row[key];
    if (val !== undefined && val !== null && String(val).length > 0) {
      return String(val);
    }
  }
  return null;
}

function movesSummary(moves: unknown): string {
  if (!Array.isArray(moves)) {
    return "";
  }
  const parts: string[] = [];
  for (const m of moves) {
    if (m && typeof m === "object") {
      const san = (m as Record<string, unknown>).move_san;
      if (typeof san === "string" && san.length > 0) {
        parts.push(san);
      }
    }
  }
  return parts.join(" ");
}

export type LogFn = (msg: string) => void;

function errorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

async function chooseMoveWithRetry(
  chooser: LlmMoveChooser,
  ctx: MovePromptContext,
  legalUci: string[],
  uciToSan: Map<string, string>,
  log?: LogFn | null,
): Promise<{ san: string; uci: string } | null> {
  let feedback: string | null = null;
  for (let attempt = 1; attempt <= 2; attempt += 1) {
    try {
      const choice = await chooser.chooseMove(ctx, feedback);
      const resolved = resolveLegalMove(ctx.fen, choice, legalUci, uciToSan);
      if (resolved) {
        return resolved;
      }
      feedback = "Your JSON did not contain a legal move_san or move_uci from the lists.";
    } catch (error) {
      feedback = `The previous call failed: ${errorMessage(error)}`;
      log?.(`[llm] chooser error for ${ctx.gameId} (attempt ${attempt}): ${feedback}`);
    }
  }
  return null;
}

export async function runLlmHeartbeatOnce(
  client: MoltChessClient,
  chooser: LlmMoveChooser,
  options: {
    myTurnLimit?: number;
    log?: LogFn | null;
    agentBasics?: AgentBasicsConfig | null;
  } = {},
): Promise<string[]> {
  const myTurnLimit = options.myTurnLimit ?? 50;
  const log = options.log ?? console.log;
  const lines: string[] = [];
  const raw = await client.chess.getMyTurnGames({ limit: myTurnLimit });
  const summaries = coerceMyTurnGames(raw);

  for (const summary of summaries) {
    const gid = gameIdFromSummary(summary);
    if (!gid) {
      continue;
    }
    let detail: unknown;
    try {
      detail = await client.chess.getGame(gid);
    } catch (err) {
      if (err instanceof MoltChessApiError) {
        log?.(`[llm] skip game (fetch failed): ${gid} ${err.message}`);
      }
      continue;
    }
    if (!detail || typeof detail !== "object") {
      continue;
    }
    const d = detail as Record<string, unknown>;
    if (!d.is_my_turn) {
      continue;
    }
    const fen = d.current_fen;
    if (typeof fen !== "string" || !fen.trim()) {
      log?.(`[llm] skip game (no FEN): ${gid}`);
      continue;
    }
    const myColor = String(d.my_color ?? "white");
    const summaryText = movesSummary(d.moves);

    const { legalSans, legalUci, uciToSan } = legalMovesFromFen(fen);
    if (!legalUci.length) {
      log?.(`[llm] skip game (no legal moves): ${gid}`);
      continue;
    }

    const ctx: MovePromptContext = {
      gameId: gid,
      fen,
      myColor,
      legalSans,
      legalUci,
      movesSummary: summaryText,
    };

    let resolved = await chooseMoveWithRetry(chooser, ctx, legalUci, uciToSan, log);
    if (!resolved) {
      const fb = firstLegalFallback({ legalSans, legalUci, uciToSan });
      log?.(`[llm] fallback move for ${gid}: ${fb.san} (${fb.uci})`);
      resolved = fb;
    }

    try {
      await client.chess.submitMove({
        game_id: gid,
        move_san: resolved.san,
        move_uci: resolved.uci,
      });
    } catch (err) {
      const msg = err instanceof MoltChessApiError ? err.message : String(err);
      const line = `[llm] submit_move failed ${gid}: ${msg}`;
      lines.push(line);
      log?.(line);
      continue;
    }

    const line = `[llm] played ${resolved.san} (${resolved.uci}) in ${gid}`;
    lines.push(line);
    log?.(line);
  }

  if (options.agentBasics !== undefined && options.agentBasics !== null) {
    const extra = await runAgentBasicsOnce(client, options.agentBasics, { log });
    lines.push(...extra);
  }

  return lines;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function runLlmHeartbeatLoop(
  client: MoltChessClient,
  chooser: LlmMoveChooser,
  options: {
    intervalSec?: number;
    myTurnLimit?: number;
    log?: LogFn | null;
    stopAfterOne?: boolean;
    agentBasics?: AgentBasicsConfig | null;
  } = {},
): Promise<void> {
  const intervalSec = options.intervalSec ?? 45;
  const myTurnLimit = options.myTurnLimit ?? 50;
  const log = options.log ?? console.log;
  const stopAfterOne = options.stopAfterOne ?? false;

  for (;;) {
    try {
      await runLlmHeartbeatOnce(client, chooser, {
        myTurnLimit,
        log,
        agentBasics: options.agentBasics,
      });
    } catch (error) {
      log?.(`[llm] heartbeat tick failed: ${errorMessage(error)}`);
    }
    if (stopAfterOne) {
      return;
    }
    await sleep(intervalSec * 1000);
  }
}
