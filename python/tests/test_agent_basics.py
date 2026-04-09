from __future__ import annotations

from moltchess.llm.agent_basics import AgentBasicsConfig, coerce_api_rows, run_agent_basics_once


def test_coerce_api_rows_list() -> None:
    raw = [{"challenge_id": "a"}, {"id": "b"}]
    assert len(coerce_api_rows(raw)) == 2


def test_coerce_api_rows_wrapped() -> None:
    raw = {"challenges": [{"challenge_id": "x"}]}
    rows = coerce_api_rows(raw)
    assert len(rows) == 1
    assert rows[0]["challenge_id"] == "x"


def test_coerce_api_rows_posts() -> None:
    raw = {"posts": [{"post_id": "p1"}]}
    assert coerce_api_rows(raw)[0]["post_id"] == "p1"


def test_run_agent_basics_mock_client() -> None:
    calls: list[tuple[str, object]] = []

    class Chess:
        def get_open_challenges(self, **kwargs):
            calls.append(("get_open_challenges", kwargs))
            return [{"challenge_id": "c1"}]

        def accept_challenge(self, cid: str):
            calls.append(("accept_challenge", cid))
            return {"ok": True}

        def list_open_tournaments(self, **kwargs):
            calls.append(("list_open_tournaments", kwargs))
            return [{"tournament_id": "t1", "entry_fee_sol": 0}]

        def join_tournament(self, tid: str):
            calls.append(("join_tournament", tid))
            return {"ok": True}

    class Feed:
        def get_unseen(self, **kwargs):
            calls.append(("get_unseen", kwargs))
            return [{"post_id": "post1"}, {"post_id": "post2"}]

    class Social:
        def like(self, payload):
            calls.append(("like", payload))
            return {"ok": True}

    class Client:
        chess = Chess()
        feed = Feed()
        social = Social()

    lines = run_agent_basics_once(Client(), AgentBasicsConfig(like_unseen_posts_max=2), log=None)
    assert any("accepted open challenge" in x for x in lines)
    assert any("joined tournament" in x for x in lines)
    assert sum(1 for c in calls if c[0] == "like") == 2
