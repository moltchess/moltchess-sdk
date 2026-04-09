from __future__ import annotations

import chess


def legal_moves_from_fen(fen: str) -> tuple[list[str], list[str], dict[str, str]]:
    board = chess.Board(fen)
    sans: list[str] = []
    ucis: list[str] = []
    uci_to_san: dict[str, str] = {}
    for move in board.legal_moves:
        uci = move.uci()
        san = board.san(move)
        sans.append(san)
        ucis.append(uci)
        uci_to_san[uci] = san
    return sans, ucis, uci_to_san


def first_legal_fallback(sans: list[str], ucis: list[str], uci_to_san: dict[str, str]) -> tuple[str, str]:
    if ucis:
        u = ucis[0]
        return uci_to_san.get(u, sans[0] if sans else ""), u
    raise ValueError("No legal moves in position")
