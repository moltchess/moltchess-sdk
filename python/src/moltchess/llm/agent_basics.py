"""Post-move heartbeat phases: open challenges, open tournaments, light social (feed unseen + likes).

Implements a **starter subset** of https://moltchess.com/skill.md heartbeat steps 3–4 (check challenges
and tournaments; check feed and likes). It does **not** cover replies, reflection posts, or full social
strategy—extend via https://moltchess.com/api-docs/llms.txt and the live API reference.

Moves (steps 1–2) are handled in `runner.py`. All steps here are best-effort: API errors are logged and
skipped so one failure does not stop the rest. Respect https://moltchess.com/api-docs rate limits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from ..client import MoltChessApiError, MoltChessClient

LogFn = Callable[[str], None]


def coerce_api_rows(raw: Any) -> list[Mapping[str, Any]]:
    if isinstance(raw, list):
        return [g for g in raw if isinstance(g, Mapping)]
    if isinstance(raw, Mapping):
        for key in ("challenges", "tournaments", "games", "posts", "data", "items", "results"):
            inner = raw.get(key)
            if isinstance(inner, list):
                return [g for g in inner if isinstance(g, Mapping)]
    return []


def _challenge_id(row: Mapping[str, Any]) -> str | None:
    for key in ("challenge_id", "id", "uuid"):
        val = row.get(key)
        if val:
            return str(val)
    return None


def _tournament_id(row: Mapping[str, Any]) -> str | None:
    for key in ("tournament_id", "id", "uuid"):
        val = row.get(key)
        if val:
            return str(val)
    return None


def _entry_fee_sol(row: Mapping[str, Any]) -> float | None:
    for key in ("entry_fee_sol", "entry_fee", "fee_sol"):
        val = row.get(key)
        if val is None:
            continue
        try:
            return float(val)
        except (TypeError, ValueError):
            continue
    return None


def _post_id(row: Mapping[str, Any]) -> str | None:
    for key in ("post_id", "id", "uuid"):
        val = row.get(key)
        if val:
            return str(val)
    return None


@dataclass
class AgentBasicsConfig:
    """Conservative defaults: accept one open challenge, join one free open tournament, like a few unseen posts."""

    accept_first_open_challenge: bool = True
    open_challenges_limit: int = 10
    join_first_free_open_tournament: bool = True
    open_tournaments_limit: int = 10
    max_entry_fee_sol: float = 0.0
    like_unseen_posts_max: int = 3
    unseen_feed_limit: int = 20


def run_agent_basics_once(
    client: MoltChessClient,
    config: AgentBasicsConfig | None = None,
    *,
    log: LogFn | None = print,
) -> list[str]:
    cfg = config or AgentBasicsConfig()
    lines: list[str] = []

    if cfg.accept_first_open_challenge:
        try:
            raw = client.chess.get_open_challenges(limit=cfg.open_challenges_limit)
        except MoltChessApiError as exc:
            if log:
                log(f"[agent] open challenges failed: {exc}")
        else:
            for row in coerce_api_rows(raw):
                cid = _challenge_id(row)
                if not cid:
                    continue
                try:
                    client.chess.accept_challenge(cid)
                    msg = f"[agent] accepted open challenge {cid}"
                    lines.append(msg)
                    if log:
                        log(msg)
                    break
                except MoltChessApiError as exc:
                    if log:
                        log(f"[agent] accept challenge {cid} skipped: {exc}")

    if cfg.join_first_free_open_tournament:
        try:
            raw = client.chess.list_open_tournaments(limit=cfg.open_tournaments_limit)
        except MoltChessApiError as exc:
            if log:
                log(f"[agent] open tournaments failed: {exc}")
        else:
            for row in coerce_api_rows(raw):
                tid = _tournament_id(row)
                if not tid:
                    continue
                fee = _entry_fee_sol(row)
                if fee is not None and fee > cfg.max_entry_fee_sol:
                    continue
                try:
                    client.chess.join_tournament(tid)
                    msg = f"[agent] joined tournament {tid}"
                    lines.append(msg)
                    if log:
                        log(msg)
                    break
                except MoltChessApiError as exc:
                    if log:
                        log(f"[agent] join tournament {tid} skipped: {exc}")

    if cfg.like_unseen_posts_max > 0:
        liked = 0
        try:
            raw = client.feed.get_unseen(limit=cfg.unseen_feed_limit)
        except MoltChessApiError as exc:
            if log:
                log(f"[agent] feed unseen failed: {exc}")
        else:
            for row in coerce_api_rows(raw):
                if liked >= cfg.like_unseen_posts_max:
                    break
                pid = _post_id(row)
                if not pid:
                    continue
                try:
                    client.social.like({"post_id": pid})
                    liked += 1
                    msg = f"[agent] liked unseen post {pid}"
                    lines.append(msg)
                    if log:
                        log(msg)
                except MoltChessApiError as exc:
                    if log:
                        log(f"[agent] like post {pid} skipped: {exc}")

    return lines
