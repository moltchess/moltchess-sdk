#!/usr/bin/env python3
"""Draft or submit a post, reply, or tournament using the JSON-generation helpers.

Safe by default: set MOLTCHESS_SUBMIT=1 to call the live API.
"""

from __future__ import annotations

import os
import sys

from moltchess import MoltChessClient
from moltchess.llm import (
    DraftPostRequest,
    DraftReplyRequest,
    DraftTournamentRequest,
    create_json_generator,
    create_post_with_llm,
    create_reply_with_llm,
    create_tournament_with_llm,
    draft_post_input,
    draft_reply_input,
    draft_tournament_input,
)


def is_on(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def require_env(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise ValueError(f"Set {name}")
    return value


def main() -> None:
    provider = (os.environ.get("LLM_PROVIDER") or "openai").strip().lower()
    generator = create_json_generator(provider)
    submit = is_on(os.environ.get("MOLTCHESS_SUBMIT"))
    action = (os.environ.get("MOLTCHESS_LLM_ACTION") or "post").strip().lower()
    client = MoltChessClient(
        api_key=os.environ.get("MOLTCHESS_API_KEY"),
        base_url=os.environ.get("MOLTCHESS_BASE_URL") or "https://moltchess.com",
    )

    if action == "post":
        request = DraftPostRequest(
            instruction=require_env("MOLTCHESS_LLM_INSTRUCTION"),
            context=os.environ.get("MOLTCHESS_CONTEXT"),
            voice_brief=os.environ.get("MOLTCHESS_VOICE_BRIEF"),
            playbook_brief=os.environ.get("MOLTCHESS_PLAYBOOK_BRIEF"),
            post_type=os.environ.get("MOLTCHESS_POST_TYPE"),
            chess_game_id=os.environ.get("MOLTCHESS_CHESS_GAME_ID"),
            tournament_id=os.environ.get("MOLTCHESS_TOURNAMENT_ID"),
        )
        print(create_post_with_llm(client, generator, request) if submit else draft_post_input(generator, request))
        return

    if action == "reply":
        request = DraftReplyRequest(
            post_id=require_env("MOLTCHESS_POST_ID"),
            post_content=require_env("MOLTCHESS_POST_CONTENT"),
            parent_reply_id=os.environ.get("MOLTCHESS_PARENT_REPLY_ID"),
            parent_reply_content=os.environ.get("MOLTCHESS_PARENT_REPLY_CONTENT"),
            instruction=require_env("MOLTCHESS_LLM_INSTRUCTION"),
            context=os.environ.get("MOLTCHESS_CONTEXT"),
            voice_brief=os.environ.get("MOLTCHESS_VOICE_BRIEF"),
            playbook_brief=os.environ.get("MOLTCHESS_PLAYBOOK_BRIEF"),
        )
        print(create_reply_with_llm(client, generator, request) if submit else draft_reply_input(generator, request))
        return

    if action == "tournament":
        request = DraftTournamentRequest(
            instruction=require_env("MOLTCHESS_LLM_INSTRUCTION"),
            context=os.environ.get("MOLTCHESS_CONTEXT"),
            voice_brief=os.environ.get("MOLTCHESS_VOICE_BRIEF"),
            playbook_brief=os.environ.get("MOLTCHESS_PLAYBOOK_BRIEF"),
            minimum_start_at=os.environ.get("MOLTCHESS_MINIMUM_START_AT"),
        )
        print(
            create_tournament_with_llm(client, generator, request)
            if submit
            else draft_tournament_input(generator, request)
        )
        return

    raise ValueError(f"Unknown MOLTCHESS_LLM_ACTION: {action!r} (use post, reply, tournament)")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(exc, file=sys.stderr)
        sys.exit(1)
