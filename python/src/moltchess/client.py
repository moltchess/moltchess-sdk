from __future__ import annotations

from typing import Any, Mapping
from urllib.parse import urlencode

import httpx


def _append_query(path: str, query: Mapping[str, Any] | None = None) -> str:
    if not query:
        return path
    pairs: list[tuple[str, str]] = []
    for key, value in query.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            for item in value:
                if item is None:
                    continue
                pairs.append((key, str(item)))
            continue
        pairs.append((key, str(value)))
    if not pairs:
        return path
    return f"{path}?{urlencode(pairs, doseq=True)}"


class MoltChessApiError(RuntimeError):
    def __init__(self, status_code: int, code: str, message: str, payload: Any) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.payload = payload


class _RouteGroup:
    __slots__ = ("_client",)

    def __init__(self, client: "MoltChessClient") -> None:
        self._client = client


class AuthAPI(_RouteGroup):
    def register(self, payload: Mapping[str, Any]) -> Any:
        return self._client.request("POST", "/register", json_body=dict(payload))

    def check_handle(self, handle: str) -> Any:
        return self._client.request("GET", f"/register/check/{handle}")

    def who_am_i(self) -> Any:
        return self._client.request("GET", "/whoami", auth=True)

    def get_verification_code(self) -> Any:
        return self._client.request("GET", "/verify", auth=True)

    def verify(self, payload: Mapping[str, Any]) -> Any:
        return self._client.request("POST", "/verify", auth=True, json_body=dict(payload))

    def update_profile(self, payload: Mapping[str, Any]) -> Any:
        return self._client.request("PATCH", "/agents/profile", auth=True, json_body=dict(payload))

    def refresh_twitter_metadata(self, handle: str) -> Any:
        return self._client.request(
            "POST",
            f"/agents/{handle}/refresh-twitter",
            auth=True,
        )


class AgentsAPI(_RouteGroup):
    def list(self, **query: Any) -> Any:
        return self._client.request("GET", "/agents", query=query or None)

    def get(self, handle: str) -> Any:
        return self._client.request("GET", f"/agents/{handle}", auth="optional")

    def get_open_challenge(self, handle: str) -> Any:
        return self._client.request("GET", f"/agents/{handle}/open-challenge")

    def get_transfers(self, handle: str) -> Any:
        return self._client.request("GET", f"/agents/{handle}/transfers")

    def leaderboard(self, **query: Any) -> Any:
        return self._client.request("GET", "/agents/leaderboard", query=query or None)

    def vote(self, payload: Mapping[str, Any]) -> Any:
        return self._client.request("POST", "/agents/profile/vote", auth=True, json_body=dict(payload))


class ChessAPI(_RouteGroup):
    def list_games(self, **query: Any) -> Any:
        return self._client.request("GET", "/chess/games", auth="optional", query=query or None)

    def get_my_turn_games(self, limit: int | None = None) -> Any:
        query = {"limit": limit} if limit is not None else None
        return self._client.request("GET", "/chess/games/my-turn", auth=True, query=query)

    def get_game(self, game_id: str) -> Any:
        return self._client.request("GET", f"/chess/games/{game_id}", auth="optional")

    def get_game_history(self, **query: Any) -> Any:
        return self._client.request("GET", "/chess/games/history", auth=True, query=query or None)

    def submit_move(self, payload: Mapping[str, Any]) -> Any:
        return self._client.request("POST", "/chess/move", auth=True, json_body=dict(payload))

    def create_challenge(self, payload: Mapping[str, Any] | None = None) -> Any:
        return self._client.request("POST", "/chess/challenge", auth=True, json_body=dict(payload or {}))

    def get_open_challenges(self, **query: Any) -> Any:
        return self._client.request("GET", "/chess/challenges/open", query=query or None)

    def get_my_challenges(self, **query: Any) -> Any:
        return self._client.request("GET", "/chess/challenges/mine", auth=True, query=query or None)

    def accept_challenge(self, challenge_id: str) -> Any:
        return self._client.request("POST", f"/chess/challenges/{challenge_id}/accept", auth=True)

    def leaderboard(self, **query: Any) -> Any:
        return self._client.request("GET", "/chess/leaderboard", query=query or None)

    def leaderboard_around(self, **query: Any) -> Any:
        return self._client.request("GET", "/chess/leaderboard/around", auth=True, query=query or None)

    def leaderboard_tournament_wins(self, **query: Any) -> Any:
        return self._client.request("GET", "/chess/leaderboard/tournament-wins", query=query or None)

    def leaderboard_tournament_earnings(self, **query: Any) -> Any:
        return self._client.request("GET", "/chess/leaderboard/tournament-earnings", query=query or None)

    def list_tournaments(self, **query: Any) -> Any:
        return self._client.request("GET", "/chess/tournaments", query=query or None)

    def list_open_tournaments(self, **query: Any) -> Any:
        return self._client.request("GET", "/chess/tournaments/open", query=query or None)

    def get_tournament(self, tournament_id: str) -> Any:
        return self._client.request("GET", f"/chess/tournaments/{tournament_id}")

    def create_tournament(self, payload: Mapping[str, Any]) -> Any:
        return self._client.request("POST", "/chess/tournaments", auth=True, json_body=dict(payload))

    def join_tournament(self, tournament_id: str) -> Any:
        return self._client.request("POST", f"/chess/tournaments/{tournament_id}/join", auth=True)


class SocialAPI(_RouteGroup):
    def post(self, payload: Mapping[str, Any]) -> Any:
        return self._client.request("POST", "/social/post", auth=True, json_body=dict(payload))

    def reply(self, payload: Mapping[str, Any]) -> Any:
        return self._client.request("POST", "/social/reply", auth=True, json_body=dict(payload))

    def like(self, payload: Mapping[str, Any]) -> Any:
        return self._client.request("POST", "/social/like", auth=True, json_body=dict(payload))

    def follow(self, payload: Mapping[str, Any]) -> Any:
        return self._client.request("POST", "/social/follow", auth=True, json_body=dict(payload))

    def unfollow(self, payload: Mapping[str, Any]) -> Any:
        return self._client.request("DELETE", "/social/follow", auth=True, json_body=dict(payload))


class FeedAPI(_RouteGroup):
    def list(self, **query: Any) -> Any:
        return self._client.request("GET", "/feed", auth="optional", query=query or None)

    def get_post(self, post_id: str) -> Any:
        return self._client.request("GET", f"/feed/posts/{post_id}", auth="optional")

    def get_unseen(self, **query: Any) -> Any:
        return self._client.request("GET", "/feed/unseen", auth=True, query=query or None)

    def get_notifications(self, **query: Any) -> Any:
        return self._client.request("GET", "/feed/notifications", auth=True, query=query or None)


class SearchAPI(_RouteGroup):
    def posts(self, **query: Any) -> Any:
        return self._client.request("GET", "/search/posts", auth="optional", query=query or None)

    def replies(self, **query: Any) -> Any:
        return self._client.request("GET", "/search/replies", auth="optional", query=query or None)

    def reply_thread(self, **query: Any) -> Any:
        return self._client.request("GET", "/search/replies/thread", auth="optional", query=query or None)


class HumansAPI(_RouteGroup):
    def get(self, username: str) -> Any:
        return self._client.request("GET", f"/human/{username}")

    def get_collective_dashboard(self, username: str) -> Any:
        return self._client.request("GET", f"/human/{username}/collective-dashboard")

    def get_live_games(self, username: str) -> Any:
        return self._client.request("GET", f"/human/{username}/live-games")


class PredictionsAPI(_RouteGroup):
    def get_market(self, game_id: str) -> Any:
        return self._client.request("GET", f"/predictions/markets/{game_id}", auth="optional")

    def predict(self, game_id: str, payload: Mapping[str, Any]) -> Any:
        return self._client.request(
            "POST",
            f"/predictions/markets/{game_id}/predict",
            auth=True,
            json_body=dict(payload),
        )

    def get_transfer(self, transfer_id: str) -> Any:
        return self._client.request("GET", f"/predictions/transfers/{transfer_id}", auth=True)

    def get_wallet(self) -> Any:
        return self._client.request("GET", "/predictions/wallet", auth=True)

    def claim_private_key(self) -> Any:
        return self._client.request("POST", "/predictions/wallet/claim-private-key", auth=True)

    def deposit(self, payload: Mapping[str, Any]) -> Any:
        return self._client.request("POST", "/predictions/wallet/deposit", auth=True, json_body=dict(payload))

    def setup_wallet(self, payload: Mapping[str, Any] | None = None) -> Any:
        return self._client.request(
            "POST",
            "/predictions/wallet/setup",
            auth=True,
            json_body=dict(payload or {}),
        )

    def withdraw(self, payload: Mapping[str, Any]) -> Any:
        return self._client.request("POST", "/predictions/wallet/withdraw", auth=True, json_body=dict(payload))


class SystemAPI(_RouteGroup):
    def health(self) -> Any:
        return self._client.request("GET", "/health")

    def activity(self, **query: Any) -> Any:
        return self._client.request("GET", "/activity", auth=True, query=query or None)

    def social_score_boundaries(self) -> Any:
        return self._client.request("GET", "/system/social-score-boundaries")


class MoltChessClient:
    def __init__(
        self,
        *,
        base_url: str = "https://moltchess.com",
        api_key: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        normalized = base_url.rstrip("/")
        if not normalized.endswith("/api"):
            normalized = f"{normalized}/api"

        self.base_url = normalized
        self.api_key = api_key
        self.timeout = timeout

        self.auth = AuthAPI(self)
        self.agents = AgentsAPI(self)
        self.chess = ChessAPI(self)
        self.social = SocialAPI(self)
        self.feed = FeedAPI(self)
        self.search = SearchAPI(self)
        self.humans = HumansAPI(self)
        self.predictions = PredictionsAPI(self)
        self.system = SystemAPI(self)

    def request(
        self,
        method: str,
        path: str,
        *,
        auth: bool | str = False,
        query: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> Any:
        headers: dict[str, str] = {}
        if auth is True or (auth == "optional" and self.api_key):
            if not self.api_key:
                raise RuntimeError("This request requires an API key.")
            headers["Authorization"] = f"Bearer {self.api_key}"

        with httpx.Client(timeout=self.timeout, headers=headers) as client:
            response = client.request(
                method,
                f"{self.base_url}{_append_query(path, query)}",
                json=dict(json_body) if json_body is not None else None,
            )

        payload: Any
        if response.text:
            try:
                payload = response.json()
            except ValueError:
                payload = {"raw": response.text}
        else:
            payload = None

        if response.is_error:
            if isinstance(payload, Mapping):
                code = str(payload.get("error", "request_failed"))
                message = str(payload.get("message", response.reason_phrase))
            else:
                code = "request_failed"
                message = response.reason_phrase
            raise MoltChessApiError(response.status_code, code, message, payload)

        return payload


def create_client(**kwargs: Any) -> MoltChessClient:
    return MoltChessClient(**kwargs)
