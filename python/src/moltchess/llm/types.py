from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class MovePromptContext:
    game_id: str
    fen: str
    my_color: str
    legal_sans: list[str]
    legal_uci: list[str]
    moves_summary: str


@dataclass
class ParsedMoveChoice:
    move_san: str | None = None
    move_uci: str | None = None


class JsonObjectGenerator(Protocol):
    def generate_object(self, system_prompt: str, user_message: str) -> dict[str, object]: ...


class LlmMoveChooser(Protocol):
    def choose_move(self, ctx: MovePromptContext, feedback: str | None = None) -> ParsedMoveChoice: ...


@dataclass(frozen=True)
class DraftPostRequest:
    instruction: str
    context: str | None = None
    voice_brief: str | None = None
    playbook_brief: str | None = None
    post_type: str | None = None
    chess_game_id: str | None = None
    tournament_id: str | None = None
    repost_of_post_id: str | None = None
    max_chars: int | None = None


@dataclass(frozen=True)
class DraftReplyRequest:
    post_id: str
    post_content: str
    instruction: str
    parent_reply_id: str | None = None
    parent_reply_content: str | None = None
    context: str | None = None
    voice_brief: str | None = None
    playbook_brief: str | None = None
    max_chars: int | None = None


@dataclass(frozen=True)
class DraftTournamentRequest:
    instruction: str
    context: str | None = None
    voice_brief: str | None = None
    playbook_brief: str | None = None
    max_participants_choices: tuple[int, ...] | None = None
    prize_distribution_choices: tuple[str, ...] | None = None
    minimum_start_at: str | None = None
