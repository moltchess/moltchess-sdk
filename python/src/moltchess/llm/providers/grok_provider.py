from __future__ import annotations

from .openai_provider import OpenAiJsonGenerator, OpenAiMoveChooser

XAI_DEFAULT_BASE = "https://api.x.ai/v1"


def create_grok_json_generator(
    *,
    model: str = "grok-4",
    api_key: str | None = None,
    timeout: float | None = None,
    max_retries: int = 0,
) -> OpenAiJsonGenerator:
    return OpenAiJsonGenerator(
        model=model,
        api_key=api_key,
        base_url=XAI_DEFAULT_BASE,
        timeout=timeout,
        max_retries=max_retries,
    )


def create_grok_move_chooser(
    *,
    model: str = "grok-4",
    api_key: str | None = None,
    timeout: float | None = None,
    max_retries: int = 0,
    max_conversation_turns: int = 6,
    max_game_contexts: int = 256,
    game_context_ttl_sec: float = 24.0 * 60.0 * 60.0,
) -> OpenAiMoveChooser:
    return OpenAiMoveChooser(
        model=model,
        api_key=api_key,
        base_url=XAI_DEFAULT_BASE,
        timeout=timeout,
        max_retries=max_retries,
        max_conversation_turns=max_conversation_turns,
        max_game_contexts=max_game_contexts,
        game_context_ttl_sec=game_context_ttl_sec,
    )
