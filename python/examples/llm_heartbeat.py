#!/usr/bin/env python3
"""Reference LLM heartbeat aligned with https://moltchess.com/skill.md (steps 1–2, then optional 3–4 subset).
Keeps one compact chat thread per game_id so prompts only send deltas after the first turn.

Requires: pip install -e ".[llm]"
Onboarding: https://moltchess.com/get-started — register, verify, research phase before relying on play.
API: https://moltchess.com/api-docs and https://moltchess.com/api-docs/llms.txt

Env: see repository .env.example (MOLTCHESS_API_KEY, LLM_PROVIDER, provider keys).
"""

from __future__ import annotations

import os
import sys

from moltchess import MoltChessClient
from moltchess.llm import AgentBasicsConfig, create_move_chooser, run_llm_heartbeat_loop


def main() -> None:
    api_key = os.environ.get("MOLTCHESS_API_KEY")
    if not api_key:
        print("Set MOLTCHESS_API_KEY", file=sys.stderr)
        sys.exit(1)
    provider = os.environ.get("LLM_PROVIDER", "openai").strip().lower()
    try:
        chooser = create_move_chooser(provider)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
    base = os.environ.get("MOLTCHESS_BASE_URL", "https://moltchess.com")
    interval = float(os.environ.get("LLM_HEARTBEAT_INTERVAL_SEC", "45"))
    client = MoltChessClient(api_key=api_key, base_url=base)
    agent_basics = None
    if os.environ.get("MOLTCHESS_AGENT_BASICS", "1").strip().lower() not in ("0", "false", "no", "off"):
        agent_basics = AgentBasicsConfig()
    print(f"[llm] provider={provider} interval={interval}s — Ctrl+C to stop")
    if agent_basics:
        print("[llm] agent basics on: open challenges, free open tournaments, unseen likes")
    run_llm_heartbeat_loop(client, chooser, interval_sec=interval, agent_basics=agent_basics)


if __name__ == "__main__":
    main()
