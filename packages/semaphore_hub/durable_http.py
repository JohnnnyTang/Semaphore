"""Authenticated W3 dispatcher; startup readiness remains the host's responsibility."""

from urllib.parse import urlsplit

from semaphore_hub.auth.service import AuthError
from semaphore_hub.http import FoundationHttp, error
from semaphore_hub.policy import REQUEST_MAX_BYTES, SESSION_COOKIE


class DurableHttp(FoundationHttp):
    def __init__(self, auth, packs, games, results):
        from semaphore_hub.games.http import GamesHttp

        super().__init__(auth, packs)
        self.game_http = GamesHttp(games, results)

    def handle(self, method, target, headers, body=b"", peer=""):
        try:
            parsed = urlsplit(target)
        except ValueError:
            return error(400, "invalid_request")
        path = parsed.path
        if not (
            path == "/api/v1/history"
            or path == "/api/v1/games"
            or path.startswith(("/api/v1/games/", "/api/v1/boards/"))
        ):
            return super().handle(method, target, headers, body, peer)
        if parsed.scheme or parsed.netloc or parsed.fragment:
            return error(400, "invalid_request")
        values = {}
        for key, value in headers:
            key = key.lower()
            if key in values and key in {
                "host",
                "origin",
                "cookie",
                "x-csrf-token",
                "content-length",
                "content-type",
                "transfer-encoding",
            }:
                return error(400, "invalid_request")
            values[key] = value
        mutation = method not in {"GET", "HEAD"}
        if not self.auth.service.policy.accepts(
            host=values.get("host", ""), origin=values.get("origin"), mutation=mutation
        ):
            return error(403, "origin_denied")
        if len(body) > REQUEST_MAX_BYTES:
            return error(413, "body_too_large")
        if (
            mutation
            and body
            and (
                values.get("content-type", "").split(";", 1)[0].strip().lower()
                != "application/json"
            )
        ):
            return error(400, "invalid_request")
        token = None
        for part in values.get("cookie", "").split(";"):
            name, sep, value = part.strip().partition("=")
            if sep and name == SESSION_COOKIE:
                if token is not None:
                    return error(400, "invalid_request")
                token = value
        try:
            principal = self.auth.service.authenticate(
                token, values.get("x-csrf-token"), mutation=mutation
            )
        except AuthError as exc:
            return error(exc.status, exc.code)
        return self.game_http.handle(principal, method, target, body)
