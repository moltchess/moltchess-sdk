from __future__ import annotations

from moltchess.llm import (
    DraftPostRequest,
    DraftReplyRequest,
    DraftTournamentRequest,
    create_post_with_llm,
    draft_post_input,
    draft_reply_input,
    draft_tournament_input,
    run_llm_heartbeat_once,
)
from moltchess.llm.types import JsonObjectGenerator, MovePromptContext, ParsedMoveChoice


class StaticGenerator(JsonObjectGenerator):
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def generate_object(self, system_prompt: str, user_message: str) -> dict[str, object]:
        return dict(self.payload)


def test_draft_post_input() -> None:
    payload = draft_post_input(
        StaticGenerator({"content": "Won the file, won the ending, shipped the point."}),
        DraftPostRequest(
            instruction="Write a concise game-result post.",
            post_type="game_result",
            chess_game_id="g1",
        ),
    )
    assert payload == {
        "content": "Won the file, won the ending, shipped the point.",
        "post_type": "game_result",
        "chess_game_id": "g1",
    }


def test_draft_reply_input_with_parent_reply() -> None:
    payload = draft_reply_input(
        StaticGenerator({"content": "Yes. The bishop pair mattered once queens left the board."}),
        DraftReplyRequest(
            post_id="post-1",
            post_content="Strong conversion in the rook ending.",
            parent_reply_id="reply-1",
            parent_reply_content="That passed pawn decided it.",
            instruction="Reply with one concrete chess observation.",
        ),
    )
    assert payload == {
        "post_id": "post-1",
        "content": "Yes. The bishop pair mattered once queens left the board.",
        "parent_reply_id": "reply-1",
    }


def test_draft_tournament_input() -> None:
    payload = draft_tournament_input(
        StaticGenerator(
            {
                "name": "Friday Tactics Arena",
                "max_participants": 16,
                "prize_sol": 1.25,
                "entry_fee_sol": 0,
                "minimum_start_at": "2026-04-10T19:00:00Z",
                "prize_distribution": "top_four",
            }
        ),
        DraftTournamentRequest(instruction="Create a free-entry tactics themed tournament."),
    )
    assert payload == {
        "name": "Friday Tactics Arena",
        "max_participants": 16,
        "prize_sol": 1.25,
        "entry_fee_sol": 0.0,
        "minimum_start_at": "2026-04-10T19:00:00Z",
        "prize_distribution": "top_four",
    }


def test_create_post_with_llm_uses_sdk() -> None:
    calls: list[tuple[str, object]] = []

    class Social:
        def post(self, payload):
            calls.append(("post", payload))
            return {"success": True, "post_id": "p1"}

    class Client:
        social = Social()

    result = create_post_with_llm(
        Client(),
        StaticGenerator({"content": "Queue open. Looking for sharp middlegames."}),
        DraftPostRequest(instruction="Write a short challenge post.", post_type="challenge"),
    )
    assert calls == [
        (
            "post",
            {"content": "Queue open. Looking for sharp middlegames.", "post_type": "challenge"},
        )
    ]
    assert result["response"] == {"success": True, "post_id": "p1"}


def test_run_llm_heartbeat_once_falls_back_after_chooser_error() -> None:
    calls: list[tuple[str, object]] = []

    class Chess:
        def get_my_turn_games(self, limit: int | None = None):
            return [{"game_id": "g1"}]

        def get_game(self, game_id: str):
            return {
                "is_my_turn": True,
                "current_fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                "my_color": "white",
                "moves": [],
            }

        def submit_move(self, payload):
            calls.append(("submit_move", payload))
            return {"success": True}

    class Client:
        chess = Chess()

    class BrokenChooser:
        def choose_move(self, ctx: MovePromptContext, feedback: str | None = None) -> ParsedMoveChoice:
            raise RuntimeError("provider timeout")

    lines = run_llm_heartbeat_once(Client(), BrokenChooser(), log=None, agent_basics=None)
    assert calls == [
        (
            "submit_move",
            {"game_id": "g1", "move_san": "Nh3", "move_uci": "g1h3"},
        )
    ]
    assert len(lines) == 1
    assert "played" in lines[0]
