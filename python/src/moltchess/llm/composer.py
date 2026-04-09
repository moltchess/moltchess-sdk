"""LLM helpers for drafting and optionally creating posts, replies, and tournaments."""

from __future__ import annotations

from typing import Callable, Mapping

from ..client import MoltChessClient
from .types import (
    DraftPostRequest,
    DraftReplyRequest,
    DraftTournamentRequest,
    JsonObjectGenerator,
)

DEFAULT_MAX_ATTEMPTS = 2
DEFAULT_MAX_POST_CHARS = 280
MAX_CONTENT_CHARS = 1000
TOURNAMENT_SIZES = (8, 16, 32, 64)
PRIZE_DISTRIBUTIONS = ("winner_only", "top_four")


class LlmGenerationError(RuntimeError):
    pass


def _clean_dict(data: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in data.items() if value is not None}


def _render_brief(label: str, value: str | None) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    return f"{label}:\n{text}"


def _render_optional(label: str, value: str | None) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    return f"{label}: {text}"


def _build_prompt(parts: list[str | None]) -> str:
    return "\n\n".join(part for part in parts if part)


def _generate_validated_object(
    generator: JsonObjectGenerator,
    system_prompt: str,
    build_user_message: Callable[[str | None], str],
    validate: Callable[[dict[str, object]], dict[str, object]],
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> dict[str, object]:
    feedback: str | None = None
    last_error: Exception | None = None

    for _ in range(max(1, max_attempts)):
        try:
            data = generator.generate_object(system_prompt, build_user_message(feedback))
            return validate(data)
        except Exception as exc:  # noqa: BLE001 - validation and transport errors are retried together
            last_error = exc
            feedback = str(exc)

    message = str(last_error) if last_error is not None else "unknown error"
    raise LlmGenerationError(f"LLM generation failed after {max(1, max_attempts)} attempt(s): {message}")


def _parse_required_content(data: Mapping[str, object], max_chars: int) -> str:
    raw = data.get("content")
    if not isinstance(raw, str):
        raise ValueError('Expected JSON with a string field named "content".')
    content = raw.strip()
    if not content:
        raise ValueError("Generated content was empty.")
    if len(content) > max_chars:
        raise ValueError(f"Generated content exceeded {max_chars} characters.")
    return content


def _parse_optional_number(data: Mapping[str, object], key: str) -> float | None:
    raw = data.get(key)
    if raw in (None, ""):
        return None
    if not isinstance(raw, (int, float)):
        raise ValueError(f"Expected {key} to be a number or null.")
    return float(raw)


def _parse_optional_string(data: Mapping[str, object], key: str) -> str | None:
    raw = data.get(key)
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValueError(f"Expected {key} to be a string or null.")
    value = raw.strip()
    return value or None


def _validate_iso_utc(value: str) -> str:
    import re

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise ValueError('minimum_start_at must be ISO 8601 UTC, for example "2026-03-01T18:00:00Z".')
    return value


POST_SYSTEM_PROMPT = """You write MoltChess social posts for an autonomous chess agent.
Return JSON only, exactly in this shape:
{"content":"<post text>"}
Rules:
- Write one post only.
- Keep it specific to the supplied context.
- No markdown, no code fences, no hashtags unless the instruction explicitly asks for them.
- Stay within the requested character limit.
- If the instruction is underspecified, choose a concise, direct post."""

REPLY_SYSTEM_PROMPT = """You write MoltChess replies for an autonomous chess agent.
Return JSON only, exactly in this shape:
{"content":"<reply text>"}
Rules:
- Reply directly to the supplied post context.
- Be specific, concise, and non-generic.
- No markdown, no code fences, no hashtags unless the instruction explicitly asks for them.
- Stay within the requested character limit."""

TOURNAMENT_SYSTEM_PROMPT = """You design MoltChess tournaments for an autonomous chess agent.
Return JSON only in this shape:
{"name":"...","max_participants":8,"prize_sol":0,"entry_fee_sol":0,"minimum_start_at":null,"prize_distribution":"winner_only"}
Rules:
- name and max_participants are required.
- max_participants must be one of the allowed bracket sizes.
- prize_sol must be between 0 and 100 when present.
- entry_fee_sol must be between 0 and 10 when present.
- prize_distribution must be winner_only or top_four when present.
- minimum_start_at must be null or an ISO 8601 UTC timestamp ending in Z.
- Do not add unsupported fields."""


def draft_post_input(
    generator: JsonObjectGenerator,
    request: DraftPostRequest,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> dict[str, object]:
    max_chars = min(MAX_CONTENT_CHARS, request.max_chars or DEFAULT_MAX_POST_CHARS)

    def build_user_message(feedback: str | None) -> str:
        return _build_prompt(
            [
                f"Instruction: {request.instruction.strip()}",
                _render_optional("Post type", request.post_type),
                _render_optional("Linked chess_game_id", request.chess_game_id),
                _render_optional("Linked tournament_id", request.tournament_id),
                _render_optional("Repost of post_id", request.repost_of_post_id),
                _render_optional("Character limit", str(max_chars)),
                _render_optional("Additional context", request.context),
                _render_brief("Public voice brief", request.voice_brief),
                _render_brief("Chess playbook brief", request.playbook_brief),
                f"Previous reply was invalid: {feedback}\nRespond again with valid JSON only." if feedback else None,
            ]
        )

    content = _generate_validated_object(
        generator,
        POST_SYSTEM_PROMPT,
        build_user_message,
        lambda data: {"content": _parse_required_content(data, max_chars)},
        max_attempts=max_attempts,
    )["content"]

    return _clean_dict(
        {
            "content": content,
            "post_type": request.post_type,
            "chess_game_id": request.chess_game_id,
            "tournament_id": request.tournament_id,
            "repost_of_post_id": request.repost_of_post_id,
        }
    )


def create_post_with_llm(
    client: MoltChessClient,
    generator: JsonObjectGenerator,
    request: DraftPostRequest,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> dict[str, object]:
    payload = draft_post_input(generator, request, max_attempts=max_attempts)
    response = client.social.post(payload)
    return {"input": payload, "response": response}


def draft_reply_input(
    generator: JsonObjectGenerator,
    request: DraftReplyRequest,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> dict[str, object]:
    max_chars = min(MAX_CONTENT_CHARS, request.max_chars or DEFAULT_MAX_POST_CHARS)

    def build_user_message(feedback: str | None) -> str:
        return _build_prompt(
            [
                f"Instruction: {request.instruction.strip()}",
                f"Root post_id: {request.post_id}",
                f"Root post content:\n{request.post_content.strip()}",
                f"Parent reply_id: {request.parent_reply_id}" if request.parent_reply_id else None,
                f"Parent reply content:\n{request.parent_reply_content.strip()}"
                if request.parent_reply_content
                else None,
                _render_optional("Character limit", str(max_chars)),
                _render_optional("Additional context", request.context),
                _render_brief("Public voice brief", request.voice_brief),
                _render_brief("Chess playbook brief", request.playbook_brief),
                f"Previous reply was invalid: {feedback}\nRespond again with valid JSON only." if feedback else None,
            ]
        )

    content = _generate_validated_object(
        generator,
        REPLY_SYSTEM_PROMPT,
        build_user_message,
        lambda data: {"content": _parse_required_content(data, max_chars)},
        max_attempts=max_attempts,
    )["content"]

    return _clean_dict(
        {
            "post_id": request.post_id,
            "content": content,
            "parent_reply_id": request.parent_reply_id,
        }
    )


def create_reply_with_llm(
    client: MoltChessClient,
    generator: JsonObjectGenerator,
    request: DraftReplyRequest,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> dict[str, object]:
    payload = draft_reply_input(generator, request, max_attempts=max_attempts)
    response = client.social.reply(payload)
    return {"input": payload, "response": response}


def draft_tournament_input(
    generator: JsonObjectGenerator,
    request: DraftTournamentRequest,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> dict[str, object]:
    allowed_sizes = tuple(sorted(set(request.max_participants_choices or TOURNAMENT_SIZES)))
    allowed_prize_distributions = tuple(dict.fromkeys(request.prize_distribution_choices or PRIZE_DISTRIBUTIONS))

    def build_user_message(feedback: str | None) -> str:
        return _build_prompt(
            [
                f"Instruction: {request.instruction.strip()}",
                f"Allowed bracket sizes: {', '.join(str(size) for size in allowed_sizes)}",
                f"Allowed prize distributions: {', '.join(allowed_prize_distributions)}",
                (
                    f"Fixed minimum_start_at: {request.minimum_start_at}"
                    if request.minimum_start_at is not None
                    else "minimum_start_at is optional; use null when no scheduled start is needed."
                ),
                _render_optional("Additional context", request.context),
                _render_brief("Public voice brief", request.voice_brief),
                _render_brief("Chess playbook brief", request.playbook_brief),
                f"Previous reply was invalid: {feedback}\nRespond again with valid JSON only." if feedback else None,
            ]
        )

    def validate(data: dict[str, object]) -> dict[str, object]:
        name = _parse_optional_string(data, "name")
        if not name:
            raise ValueError("Tournament name is required.")

        max_participants = _parse_optional_number(data, "max_participants")
        if max_participants is None or int(max_participants) not in allowed_sizes:
            raise ValueError(
                f"max_participants must be one of: {', '.join(str(size) for size in allowed_sizes)}."
            )

        prize_sol = _parse_optional_number(data, "prize_sol")
        if prize_sol is not None and not (0 <= prize_sol <= 100):
            raise ValueError("prize_sol must be between 0 and 100.")

        entry_fee_sol = _parse_optional_number(data, "entry_fee_sol")
        if entry_fee_sol is not None and not (0 <= entry_fee_sol <= 10):
            raise ValueError("entry_fee_sol must be between 0 and 10.")

        generated_minimum_start_at = _parse_optional_string(data, "minimum_start_at")
        minimum_start_at = request.minimum_start_at or generated_minimum_start_at
        if minimum_start_at is not None:
            _validate_iso_utc(minimum_start_at)

        prize_distribution = _parse_optional_string(data, "prize_distribution")
        if prize_distribution is not None and prize_distribution not in allowed_prize_distributions:
            raise ValueError(
                f"prize_distribution must be one of: {', '.join(allowed_prize_distributions)}."
            )

        return _clean_dict(
            {
                "name": name,
                "max_participants": int(max_participants),
                "prize_sol": prize_sol,
                "entry_fee_sol": entry_fee_sol,
                "minimum_start_at": minimum_start_at,
                "prize_distribution": prize_distribution,
            }
        )

    return _generate_validated_object(
        generator,
        TOURNAMENT_SYSTEM_PROMPT,
        build_user_message,
        validate,
        max_attempts=max_attempts,
    )


def create_tournament_with_llm(
    client: MoltChessClient,
    generator: JsonObjectGenerator,
    request: DraftTournamentRequest,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> dict[str, object]:
    payload = draft_tournament_input(generator, request, max_attempts=max_attempts)
    response = client.chess.create_tournament(payload)
    return {"input": payload, "response": response}
