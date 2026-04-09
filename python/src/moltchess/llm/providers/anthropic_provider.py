from __future__ import annotations

import time
from dataclasses import dataclass, field

import anthropic

from ..jsonutil import extract_json_object, parse_move_choice
from ..prompt import SYSTEM_PROMPT, build_user_message
from ..types import JsonObjectGenerator, MovePromptContext, ParsedMoveChoice


@dataclass
class _ConversationState:
    messages: list[dict[str, str]] = field(default_factory=list)
    last_moves_summary: str | None = None
    last_touched_at: float = 0.0


class AnthropicJsonGenerator(JsonObjectGenerator):
    def __init__(
        self,
        *,
        model: str = "claude-sonnet-4-6",
        api_key: str | None = None,
        timeout: float | None = None,
        max_retries: int = 0,
    ) -> None:
        kwargs: dict[str, object] = {"max_retries": max_retries}
        if api_key is not None:
            kwargs["api_key"] = api_key
        if timeout is not None:
            kwargs["timeout"] = timeout
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model

    def _generate_reply(self, system_prompt: str, messages: list[dict[str, str]]) -> tuple[str, dict[str, object]]:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            temperature=0.2,
            system=system_prompt,
            messages=messages,
        )
        parts: list[str] = []
        for block in message.content:
            if block.type == "text":
                parts.append(block.text)
        text = "\n".join(parts) if parts else "{}"
        data = extract_json_object(text)
        return text, dict(data)

    def generate_object(self, system_prompt: str, user_message: str) -> dict[str, object]:
        _, data = self._generate_reply(system_prompt, [{"role": "user", "content": user_message}])
        return data


class AnthropicMoveChooser(AnthropicJsonGenerator):
    def __init__(
        self,
        *,
        model: str = "claude-sonnet-4-6",
        api_key: str | None = None,
        timeout: float | None = None,
        max_retries: int = 0,
        max_conversation_turns: int = 6,
        max_game_contexts: int = 256,
        game_context_ttl_sec: float = 24.0 * 60.0 * 60.0,
    ) -> None:
        super().__init__(
            model=model,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        self._max_conversation_turns = max(1, max_conversation_turns)
        self._max_game_contexts = max(1, max_game_contexts)
        self._game_context_ttl_sec = max(game_context_ttl_sec, 60.0)
        self._sessions: dict[str, _ConversationState] = {}

    def choose_move(self, ctx: MovePromptContext, feedback: str | None = None) -> ParsedMoveChoice:
        now = time.time()
        self._prune_sessions(now)
        session = self._get_session(ctx.game_id, now)
        user = build_user_message(
            ctx,
            feedback,
            previous_moves_summary=session.last_moves_summary,
        )
        text, data = self._generate_reply(SYSTEM_PROMPT, [*session.messages, {"role": "user", "content": user}])
        san, uci = parse_move_choice(data)

        session.messages = self._trim_messages(
            [
                *session.messages,
                {"role": "user", "content": user},
                {"role": "assistant", "content": text},
            ]
        )
        session.last_moves_summary = ctx.moves_summary
        session.last_touched_at = time.time()
        return ParsedMoveChoice(move_san=san, move_uci=uci)

    def _get_session(self, game_id: str, now: float) -> _ConversationState:
        session = self._sessions.get(game_id)
        if session is None:
            session = _ConversationState(last_touched_at=now)
            self._sessions[game_id] = session
            self._prune_sessions(now)
            return session
        session.last_touched_at = now
        return session

    def _trim_messages(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        max_messages = self._max_conversation_turns * 2
        if len(messages) <= max_messages:
            return messages
        return messages[-max_messages:]

    def _prune_sessions(self, now: float) -> None:
        expired = [
            game_id
            for game_id, session in self._sessions.items()
            if now - session.last_touched_at > self._game_context_ttl_sec
        ]
        for game_id in expired:
            self._sessions.pop(game_id, None)

        while len(self._sessions) > self._max_game_contexts:
            oldest_game_id = min(self._sessions.items(), key=lambda item: item[1].last_touched_at)[0]
            self._sessions.pop(oldest_game_id, None)
