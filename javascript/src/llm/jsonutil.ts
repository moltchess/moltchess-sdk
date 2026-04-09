import type { ParsedMoveChoice } from "./types.js";

export function extractJsonObject(text: string): Record<string, unknown> {
  const trimmed = text.trim();
  const fence = trimmed.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/);
  if (fence?.[1]) {
    return JSON.parse(fence[1]) as Record<string, unknown>;
  }
  return JSON.parse(trimmed) as Record<string, unknown>;
}

export function parseMoveChoice(data: Record<string, unknown>): ParsedMoveChoice {
  const sanRaw = data.move_san;
  const uciRaw = data.move_uci;
  let moveSan: string | null | undefined;
  let moveUci: string | null | undefined;
  if (typeof sanRaw === "string") {
    const s = sanRaw.trim();
    moveSan = s.length ? s : undefined;
  }
  if (typeof uciRaw === "string") {
    const u = uciRaw.trim().toLowerCase();
    moveUci = u.length ? u : undefined;
  }
  return { moveSan, moveUci };
}
