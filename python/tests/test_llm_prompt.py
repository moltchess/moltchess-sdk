from __future__ import annotations

import json

from moltchess.llm.prompt import build_user_message, summarize_move_delta
from moltchess.llm.providers.openai_provider import OpenAiMoveChooser
from moltchess.llm.types import MovePromptContext


class RecordingMoveChooser(OpenAiMoveChooser):
    def __init__(self) -> None:
        super().__init__(api_key="test-key")
        self.calls: list[list[dict[str, str]]] = []
        self._replies = [
            '{"move_san":"Nf3","move_uci":"g1f3"}',
            '{"move_san":"Bc4","move_uci":"f1c4"}',
            '{"move_san":"d4","move_uci":"d2d4"}',
        ]

    def _generate_reply(self, system_prompt: str, messages: list[dict[str, str]]) -> tuple[str, dict[str, object]]:
        del system_prompt
        self.calls.append([dict(message) for message in messages])
        text = self._replies.pop(0)
        return text, json.loads(text)


def make_ctx(**overrides: object) -> MovePromptContext:
    base = {
        "game_id": "g1",
        "fen": "fen",
        "my_color": "white",
        "legal_sans": ["Nf3"],
        "legal_uci": ["g1f3"],
        "moves_summary": "e4 e5",
    }
    base.update(overrides)
    return MovePromptContext(**base)


def test_summarize_move_delta_append_only() -> None:
    delta = summarize_move_delta("e4 e5", "e4 e5 Nf3 Nc6")
    assert delta.mode == "continue"
    assert delta.new_moves == ["Nf3", "Nc6"]


def test_build_user_message_compacts_follow_up_turns() -> None:
    text = build_user_message(
        make_ctx(moves_summary="e4 e5 Nf3 Nc6"),
        previous_moves_summary="e4 e5",
    )
    assert "Continue the same game thread. Do not repeat prior analysis." in text
    assert "New SAN moves since your last prompt: Nf3 Nc6" in text
    assert "Full move history (SAN)" not in text


def test_openai_move_chooser_keeps_game_threads_separate() -> None:
    chooser = RecordingMoveChooser()

    chooser.choose_move(make_ctx(game_id="g1", moves_summary="e4 e5"))
    chooser.choose_move(
        make_ctx(
            game_id="g1",
            moves_summary="e4 e5 Nf3 Nc6",
            legal_sans=["Bc4"],
            legal_uci=["f1c4"],
        )
    )
    chooser.choose_move(
        make_ctx(
            game_id="g2",
            moves_summary="d4 d5",
            legal_sans=["c4"],
            legal_uci=["c2c4"],
        )
    )

    assert len(chooser.calls[0]) == 1
    assert "This is the first prompt for this game thread." in chooser.calls[0][0]["content"]

    assert len(chooser.calls[1]) == 3
    assert "New SAN moves since your last prompt: Nf3 Nc6" in chooser.calls[1][2]["content"]
    assert "Full move history (SAN)" not in chooser.calls[1][2]["content"]

    assert len(chooser.calls[2]) == 1
    assert "game_id: g2" in chooser.calls[2][0]["content"]
    assert "This is the first prompt for this game thread." in chooser.calls[2][0]["content"]
