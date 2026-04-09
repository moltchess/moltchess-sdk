from __future__ import annotations

import os

from .providers.anthropic_provider import AnthropicJsonGenerator, AnthropicMoveChooser
from .providers.grok_provider import create_grok_json_generator, create_grok_move_chooser
from .providers.openai_provider import OpenAiJsonGenerator, OpenAiMoveChooser
from .types import JsonObjectGenerator, LlmMoveChooser


def _timeout_from_env() -> float | None:
    raw = os.environ.get("LLM_TIMEOUT_SEC")
    if raw is None:
        raw = os.environ.get("LLM_TIMEOUT_MS")
        if raw is None:
            return 20.0
        return max(float(raw) / 1000.0, 1.0)
    return max(float(raw), 1.0)


def _max_retries_from_env() -> int:
    raw = os.environ.get("LLM_MAX_RETRIES")
    return max(int(raw), 0) if raw is not None else 0


def create_move_chooser(
    provider: str,
    *,
    openai_model: str | None = None,
    anthropic_model: str | None = None,
    grok_model: str | None = None,
    openai_api_key: str | None = None,
    anthropic_api_key: str | None = None,
    xai_api_key: str | None = None,
    timeout: float | None = None,
    max_retries: int | None = None,
) -> LlmMoveChooser:
    p = provider.strip().lower()
    timeout = timeout if timeout is not None else _timeout_from_env()
    max_retries = max_retries if max_retries is not None else _max_retries_from_env()
    if p == "openai":
        return OpenAiMoveChooser(
            model=openai_model or os.environ.get("OPENAI_MODEL", "gpt-5.4-mini"),
            api_key=openai_api_key or os.environ.get("OPENAI_API_KEY"),
            timeout=timeout,
            max_retries=max_retries,
        )
    if p == "anthropic":
        return AnthropicMoveChooser(
            model=anthropic_model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            api_key=anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY"),
            timeout=timeout,
            max_retries=max_retries,
        )
    if p == "grok":
        return create_grok_move_chooser(
            model=grok_model or os.environ.get("XAI_MODEL", "grok-4"),
            api_key=xai_api_key or os.environ.get("XAI_API_KEY"),
            timeout=timeout,
            max_retries=max_retries,
        )
    raise ValueError(f"Unknown LLM provider: {provider!r} (use openai, anthropic, grok)")


def create_json_generator(
    provider: str,
    *,
    openai_model: str | None = None,
    anthropic_model: str | None = None,
    grok_model: str | None = None,
    openai_api_key: str | None = None,
    anthropic_api_key: str | None = None,
    xai_api_key: str | None = None,
    timeout: float | None = None,
    max_retries: int | None = None,
) -> JsonObjectGenerator:
    p = provider.strip().lower()
    timeout = timeout if timeout is not None else _timeout_from_env()
    max_retries = max_retries if max_retries is not None else _max_retries_from_env()
    if p == "openai":
        return OpenAiJsonGenerator(
            model=openai_model or os.environ.get("OPENAI_MODEL", "gpt-5.4-mini"),
            api_key=openai_api_key or os.environ.get("OPENAI_API_KEY"),
            timeout=timeout,
            max_retries=max_retries,
        )
    if p == "anthropic":
        return AnthropicJsonGenerator(
            model=anthropic_model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            api_key=anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY"),
            timeout=timeout,
            max_retries=max_retries,
        )
    if p == "grok":
        return create_grok_json_generator(
            model=grok_model or os.environ.get("XAI_MODEL", "grok-4"),
            api_key=xai_api_key or os.environ.get("XAI_API_KEY"),
            timeout=timeout,
            max_retries=max_retries,
        )
    raise ValueError(f"Unknown LLM provider: {provider!r} (use openai, anthropic, grok)")
