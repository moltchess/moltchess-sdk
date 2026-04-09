from __future__ import annotations

from moltchess.llm.board import first_legal_fallback, legal_moves_from_fen
from moltchess.llm.jsonutil import extract_json_object, parse_move_choice
from moltchess.llm.types import ParsedMoveChoice
from moltchess.llm.validate import resolve_legal_move


def test_starting_position_legal_moves() -> None:
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    sans, ucis, u2s = legal_moves_from_fen(fen)
    assert len(ucis) == 20
    assert "e2e4" in ucis
    assert u2s["e2e4"] == "e4"


def test_resolve_legal_uci() -> None:
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    sans, ucis, u2s = legal_moves_from_fen(fen)
    resolved = resolve_legal_move(
        fen,
        ParsedMoveChoice(move_uci="e2e4"),
        sans,
        ucis,
        u2s,
    )
    assert resolved is not None
    san, uci = resolved
    assert uci == "e2e4"
    assert san == "e4"


def test_resolve_invalid_returns_none() -> None:
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    sans, ucis, u2s = legal_moves_from_fen(fen)
    assert resolve_legal_move(fen, ParsedMoveChoice(move_uci="e2e5"), sans, ucis, u2s) is None


def test_first_legal_fallback() -> None:
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    sans, ucis, u2s = legal_moves_from_fen(fen)
    san, uci = first_legal_fallback(sans, ucis, u2s)
    assert uci in ucis
    assert san == u2s[uci]


def test_extract_json_object_with_fence() -> None:
    text = 'Here:\n```json\n{"move_san":"e4","move_uci":"e2e4"}\n```'
    data = extract_json_object(text)
    assert parse_move_choice(data) == ("e4", "e2e4")


def test_extract_json_plain() -> None:
    data = extract_json_object('{"move_san":"Nf3"}')
    san, uci = parse_move_choice(data)
    assert san == "Nf3"
    assert uci is None
