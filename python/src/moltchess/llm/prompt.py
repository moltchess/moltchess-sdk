from __future__ import annotations

from dataclasses import dataclass

from .types import MovePromptContext

SYSTEM_PROMPT = """You are a chess move selector for a MoltChess autonomous agent.
Each game_id is an independent chat thread. Keep separate context per game.
After the first turn, treat prior messages in the same thread as context and avoid repeating full-history analysis.
The latest FEN and legal move lists are always authoritative, even if earlier thread state appears inconsistent.
You MUST choose exactly one move from the provided legal moves only.
Reply with a single JSON object and no other text, in this shape:
{"move_san":"<SAN>","move_uci":"<UCI>"}
Use standard algebraic notation (SAN) that appears in the legal list. You may include an optional "rationale" string field; it will be ignored by the server.
If you cannot decide, pick any legal move from the list."""


@dataclass(frozen=True)
class MoveSummaryDelta:
    mode: str
    new_moves: list[str]


def _split_moves(summary: str | None) -> list[str]:
    if not summary:
        return []
    trimmed = summary.strip()
    return trimmed.split() if trimmed else []


def summarize_move_delta(previous_moves_summary: str | None, current_moves_summary: str) -> MoveSummaryDelta:
    if previous_moves_summary is None:
        return MoveSummaryDelta(mode="initial", new_moves=_split_moves(current_moves_summary))

    previous = _split_moves(previous_moves_summary)
    current = _split_moves(current_moves_summary)

    common = 0
    while common < len(previous) and common < len(current) and previous[common] == current[common]:
        common += 1

    if common != len(previous):
        return MoveSummaryDelta(mode="resync", new_moves=current)

    return MoveSummaryDelta(mode="continue", new_moves=current[common:])


def build_user_message(
    ctx: MovePromptContext,
    feedback: str | None = None,
    *,
    previous_moves_summary: str | None = None,
) -> str:
    delta = summarize_move_delta(previous_moves_summary, ctx.moves_summary)
    lines = [
        f"game_id: {ctx.game_id}",
        f"You play as: {ctx.my_color}",
    ]

    if delta.mode == "initial":
        lines.append("This is the first prompt for this game thread.")
        lines.append(f"Full move history (SAN): {ctx.moves_summary or '(start)'}")
    elif delta.mode == "resync":
        lines.append("Reset your internal game state to this authoritative snapshot.")
        lines.append(f"Full move history (SAN): {ctx.moves_summary or '(start)'}")
    elif delta.new_moves:
        lines.append("Continue the same game thread. Do not repeat prior analysis.")
        lines.append(f"New SAN moves since your last prompt: {' '.join(delta.new_moves)}")
    else:
        lines.append("No new board moves were played since your last prompt. Re-evaluate the same position.")

    lines.extend(
        [
            f"Authoritative FEN: {ctx.fen}",
            f"Legal SAN moves ({len(ctx.legal_sans)}): {', '.join(ctx.legal_sans)}",
            f"Legal UCI moves: {', '.join(ctx.legal_uci)}",
        ]
    )
    if feedback:
        lines.append(f"Previous reply was invalid: {feedback}")
        lines.append("Respond again with valid JSON and a move from the legal lists.")
    return "\n".join(lines)
