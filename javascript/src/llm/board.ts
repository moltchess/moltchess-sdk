import { Chess } from "chess.js";

export interface LegalMovesBundle {
  legalSans: string[];
  legalUci: string[];
  uciToSan: Map<string, string>;
}

export function legalMovesFromFen(fen: string): LegalMovesBundle {
  const chess = new Chess(fen);
  const verbose = chess.moves({ verbose: true });
  const legalSans: string[] = [];
  const legalUci: string[] = [];
  const uciToSan = new Map<string, string>();
  for (const m of verbose) {
    const uci = m.from + m.to + (m.promotion ?? "");
    legalSans.push(m.san);
    legalUci.push(uci);
    uciToSan.set(uci, m.san);
  }
  return { legalSans, legalUci, uciToSan };
}

export function firstLegalFallback(bundle: LegalMovesBundle): { san: string; uci: string } {
  const uci = bundle.legalUci[0];
  if (!uci) {
    throw new Error("No legal moves in position");
  }
  const san = bundle.uciToSan.get(uci) ?? bundle.legalSans[0] ?? "";
  return { san, uci };
}
