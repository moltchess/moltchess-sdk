import { Chess } from "chess.js";

import type { ParsedMoveChoice } from "./types.js";

export function resolveLegalMove(
  fen: string,
  choice: ParsedMoveChoice,
  legalUci: string[],
  uciToSan: Map<string, string>,
): { san: string; uci: string } | null {
  const ucisSet = new Set(legalUci);

  if (choice.moveUci) {
    const u = choice.moveUci.toLowerCase();
    if (ucisSet.has(u)) {
      return { san: uciToSan.get(u) ?? "", uci: u };
    }
  }

  if (choice.moveSan) {
    const chess = new Chess(fen);
    const played = chess.move(choice.moveSan.trim());
    if (played) {
      const uci = played.from + played.to + (played.promotion ?? "");
      if (ucisSet.has(uci)) {
        return { san: played.san, uci };
      }
    }
  }
  return null;
}
