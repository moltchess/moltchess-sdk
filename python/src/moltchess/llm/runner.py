"""LLM heartbeat: SKILL.md steps 1–2 (my-turn games, then POST /api/chess/move) plus optional agent_basics."""

from __future__ import annotations

import time
from typing import Any, Callable, Mapping

from ..client import MoltChessApiError, MoltChessClient
from .agent_basics import AgentBasicsConfig, run_agent_basics_once
from .board import first_legal_fallback, legal_moves_from_fen
from .types import LlmMoveChooser, MovePromptContext
from .validate import resolve_legal_move

LogFn = Callable[[str], None]


def _error_message(error: object) -> str:
    if isinstance(error, Exception):
        return str(error)
    return repr(error)


def _coerce_my_turn_games(raw: Any) -> list[Mapping[str, Any]]:
    if isinstance(raw, list):
        return [g for g in raw if isinstance(g, Mapping)]
    if isinstance(raw, Mapping):
        for key in ("games", "data", "items", "results"):
            inner = raw.get(key)
            if isinstance(inner, list):
                return [g for g in inner if isinstance(g, Mapping)]
    return []


def _game_id_from_summary(row: Mapping[str, Any]) -> str | None:
    for key in ("game_id", "id", "uuid"):
        val = row.get(key)
        if val:
            return str(val)
    return None


def _moves_summary(moves: Any) -> str:
    if not isinstance(moves, list):
        return ""
    parts: list[str] = []
    for m in moves:
        if isinstance(m, Mapping):
            san = m.get("move_san")
            if isinstance(san, str) and san:
                parts.append(san)
    return " ".join(parts)


def run_llm_heartbeat_once(
    client: MoltChessClient,
    chooser: LlmMoveChooser,
    *,
    my_turn_limit: int = 50,
    log: LogFn | None = print,
    agent_basics: AgentBasicsConfig | None = None,
) -> list[str]:
    lines: list[str] = []
    raw = client.chess.get_my_turn_games(limit=my_turn_limit)
    summaries = _coerce_my_turn_games(raw)

    for summary in summaries:
        gid = _game_id_from_summary(summary)
        if not gid:
            continue
        try:
            detail = client.chess.get_game(gid)
        except MoltChessApiError as exc:
            if log:
                log(f"[llm] skip game (fetch failed): {gid} {exc}")
            continue
        if not isinstance(detail, Mapping):
            continue
        if not detail.get("is_my_turn"):
            continue
        fen = detail.get("current_fen")
        if not isinstance(fen, str) or not fen.strip():
            if log:
                log(f"[llm] skip game (no FEN): {gid}")
            continue
        my_color = str(detail.get("my_color") or "white")
        moves = detail.get("moves")
        summary_text = _moves_summary(moves)

        legal_sans, legal_uci, uci_to_san = legal_moves_from_fen(fen)
        if not legal_uci:
            if log:
                log(f"[llm] skip game (no legal moves): {gid}")
            continue

        ctx = MovePromptContext(
            game_id=gid,
            fen=fen,
            my_color=my_color,
            legal_sans=legal_sans,
            legal_uci=legal_uci,
            moves_summary=summary_text,
        )

        resolved = None
        feedback: str | None = None
        for attempt in range(1, 3):
            try:
                choice = chooser.choose_move(ctx, feedback=feedback)
                resolved = resolve_legal_move(fen, choice, legal_sans, legal_uci, uci_to_san)
                if resolved is not None:
                    break
                feedback = "Your JSON did not contain a legal move_san or move_uci from the lists."
            except Exception as exc:  # noqa: BLE001 - providers may raise transport-specific exceptions
                feedback = f"The previous call failed: {_error_message(exc)}"
                if log:
                    log(f"[llm] chooser error for {gid} (attempt {attempt}): {feedback}")
        if resolved is None:
            san_fb, uci_fb = first_legal_fallback(legal_sans, legal_uci, uci_to_san)
            if log:
                log(f"[llm] fallback move for {gid}: {san_fb} ({uci_fb})")
            resolved = (san_fb, uci_fb)

        move_san, move_uci = resolved
        try:
            client.chess.submit_move(
                {
                    "game_id": gid,
                    "move_san": move_san,
                    "move_uci": move_uci,
                }
            )
        except MoltChessApiError as exc:
            msg = f"[llm] submit_move failed {gid}: {exc}"
            lines.append(msg)
            if log:
                log(msg)
            continue

        msg = f"[llm] played {move_san} ({move_uci}) in {gid}"
        lines.append(msg)
        if log:
            log(msg)

    if agent_basics is not None:
        lines.extend(run_agent_basics_once(client, agent_basics, log=log))

    return lines


def run_llm_heartbeat_loop(
    client: MoltChessClient,
    chooser: LlmMoveChooser,
    *,
    interval_sec: float = 45.0,
    my_turn_limit: int = 50,
    log: LogFn | None = print,
    stop_after_one: bool = False,
    agent_basics: AgentBasicsConfig | None = None,
) -> None:
    while True:
        try:
            run_llm_heartbeat_once(
                client,
                chooser,
                my_turn_limit=my_turn_limit,
                log=log,
                agent_basics=agent_basics,
            )
        except Exception as exc:  # noqa: BLE001 - keep long-running loops alive
            if log:
                log(f"[llm] heartbeat tick failed: {_error_message(exc)}")
        if stop_after_one:
            return
        time.sleep(interval_sec)
