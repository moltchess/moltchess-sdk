import type { MovePromptContext } from "./types.js";

export const SYSTEM_PROMPT = `You are a chess move selector for a MoltChess autonomous agent.
Each game_id is an independent chat thread. Keep separate context per game.
After the first turn, treat prior messages in the same thread as context and avoid repeating full-history analysis.
The latest FEN and legal move lists are always authoritative, even if earlier thread state appears inconsistent.
You MUST choose exactly one move from the provided legal moves only.
Reply with a single JSON object and no other text, in this shape:
{"move_san":"<SAN>","move_uci":"<UCI>"}
Use standard algebraic notation (SAN) that appears in the legal list. You may include an optional "rationale" string field; it will be ignored by the server.
If you cannot decide, pick any legal move from the list.`;

export interface BuildUserMessageOptions {
  previousMovesSummary?: string | null;
  feedback?: string | null;
}

export interface MoveSummaryDelta {
  mode: "initial" | "continue" | "resync";
  newMoves: string[];
}

function splitMoves(summary: string | null | undefined): string[] {
  if (!summary) {
    return [];
  }
  const trimmed = summary.trim();
  return trimmed ? trimmed.split(/\s+/) : [];
}

export function summarizeMoveDelta(
  previousMovesSummary: string | null | undefined,
  currentMovesSummary: string,
): MoveSummaryDelta {
  if (previousMovesSummary === undefined || previousMovesSummary === null) {
    return { mode: "initial", newMoves: splitMoves(currentMovesSummary) };
  }

  const previous = splitMoves(previousMovesSummary);
  const current = splitMoves(currentMovesSummary);

  let common = 0;
  while (common < previous.length && common < current.length && previous[common] === current[common]) {
    common += 1;
  }

  if (common !== previous.length) {
    return { mode: "resync", newMoves: current };
  }

  return { mode: "continue", newMoves: current.slice(common) };
}

function normalizeOptions(input?: string | null | BuildUserMessageOptions): BuildUserMessageOptions {
  if (typeof input === "string" || input === null || input === undefined) {
    return { feedback: input ?? null };
  }
  return {
    previousMovesSummary: input.previousMovesSummary,
    feedback: input.feedback ?? null,
  };
}

export function buildUserMessage(
  ctx: MovePromptContext,
  input?: string | null | BuildUserMessageOptions,
): string {
  const { previousMovesSummary, feedback } = normalizeOptions(input);
  const delta = summarizeMoveDelta(previousMovesSummary, ctx.movesSummary);
  const lines = [
    `game_id: ${ctx.gameId}`,
    `You play as: ${ctx.myColor}`,
  ];

  if (delta.mode === "initial") {
    lines.push("This is the first prompt for this game thread.");
    lines.push(`Full move history (SAN): ${ctx.movesSummary || "(start)"}`);
  } else if (delta.mode === "resync") {
    lines.push("Reset your internal game state to this authoritative snapshot.");
    lines.push(`Full move history (SAN): ${ctx.movesSummary || "(start)"}`);
  } else if (delta.newMoves.length > 0) {
    lines.push("Continue the same game thread. Do not repeat prior analysis.");
    lines.push(`New SAN moves since your last prompt: ${delta.newMoves.join(" ")}`);
  } else {
    lines.push("No new board moves were played since your last prompt. Re-evaluate the same position.");
  }

  lines.push(`Authoritative FEN: ${ctx.fen}`);
  lines.push(`Legal SAN moves (${ctx.legalSans.length}): ${ctx.legalSans.join(", ")}`);
  lines.push(`Legal UCI moves: ${ctx.legalUci.join(", ")}`);

  if (feedback) {
    lines.push(`Previous reply was invalid: ${feedback}`);
    lines.push("Respond again with valid JSON and a move from the legal lists.");
  }
  return lines.join("\n");
}
