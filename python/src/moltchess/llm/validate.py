from __future__ import annotations

import chess

from .board import legal_moves_from_fen
from .types import ParsedMoveChoice


def resolve_legal_move(
    fen: str,
    choice: ParsedMoveChoice,
    legal_sans: list[str],
    legal_uci: list[str],
    uci_to_san: dict[str, str],
) -> tuple[str, str] | None:
    sans_set = set(legal_sans)
    ucis_set = set(legal_uci)

    if choice.move_uci and choice.move_uci in ucis_set:
        u = choice.move_uci
        return uci_to_san[u], u

    if choice.move_san:
        raw = choice.move_san.strip()
        if raw in sans_set:
            board = chess.Board(fen)
            for m in board.legal_moves:
                if board.san(m) == raw:
                    return raw, m.uci()
        board = chess.Board(fen)
        try:
            move = board.parse_san(raw)
        except ValueError:
            return None
        if move in board.legal_moves:
            return board.san(move), move.uci()
    return None
