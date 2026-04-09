import { describe, expect, it } from "vitest";

import { firstLegalFallback, legalMovesFromFen } from "./board.js";
import { extractJsonObject, parseMoveChoice } from "./jsonutil.js";
import { resolveLegalMove } from "./validate.js";

describe("legalMovesFromFen", () => {
  it("lists e2e4 from start", () => {
    const fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
    const { legalSans, legalUci, uciToSan } = legalMovesFromFen(fen);
    expect(legalUci).toContain("e2e4");
    expect(uciToSan.get("e2e4")).toBe("e4");
    expect(legalSans.length).toBe(20);
  });
});

describe("resolveLegalMove", () => {
  it("accepts legal UCI", () => {
    const fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
    const { legalUci, uciToSan } = legalMovesFromFen(fen);
    const r = resolveLegalMove(fen, { moveUci: "e2e4" }, legalUci, uciToSan);
    expect(r).toEqual({ san: "e4", uci: "e2e4" });
  });

  it("rejects illegal UCI", () => {
    const fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
    const { legalUci, uciToSan } = legalMovesFromFen(fen);
    expect(resolveLegalMove(fen, { moveUci: "e2e5" }, legalUci, uciToSan)).toBeNull();
  });
});

describe("firstLegalFallback", () => {
  it("returns a legal pair", () => {
    const fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
    const bundle = legalMovesFromFen(fen);
    const { san, uci } = firstLegalFallback(bundle);
    expect(bundle.legalUci).toContain(uci);
    expect(bundle.uciToSan.get(uci)).toBe(san);
  });
});

describe("jsonutil", () => {
  it("parses fenced JSON", () => {
    const text = '```json\n{"move_san":"e4","move_uci":"e2e4"}\n```';
    const data = extractJsonObject(text);
    expect(parseMoveChoice(data)).toMatchObject({ moveSan: "e4", moveUci: "e2e4" });
  });
});
