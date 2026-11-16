"""Authenticated W2 account and pack handler composition, without a listener.

W3 owns game/results and recovery. A host must finish startup recovery before
exposing this dispatcher; it deliberately has no game or fixture fallback.
"""

from urllib.parse import parse_qsl, unquote, urlsplit

from semaphore_hub.auth import AuthHttp, Response
from semaphore_hub.repositories import NotFound


def error(status, code):
    return Response(
        status, {"code": code, "message": code.replace("_", " ")}, {"Cache-Control": "no-store"}
    )


class FoundationHttp:
    def __init__(self, auth, packs):
        self.auth = AuthHttp(auth)
        self.packs = packs

    def handle(self, method, target, headers, body=b"", peer=""):
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or parsed.fragment:
            return error(400, "invalid_request")
        path = parsed.path
        if path == "/api/v1/config" or path.startswith("/api/v1/auth/"):
            if parsed.query:
                return error(400, "invalid_request")
            return self.auth.handle(method, path, headers, body, peer)
        # Reuse the account parser's duplicate/header/Host/Origin/session checks.
        # Only GET routes are present; no state-changing request is disguised as a read.
        if method != "GET":
            return error(404, "not_found")
        guard = self.auth.handle("GET", "/api/v1/auth/session", headers, body, peer)
        if guard.status != 200:
            return guard
        if body:
            return error(400, "invalid_request")
        try:
            pairs = parse_qsl(
                parsed.query, keep_blank_values=True, strict_parsing=True, max_num_fields=2
            )
            query = dict(pairs)
            if len(query) != len(pairs) or set(query) - {"limit", "cursor"}:
                return error(400, "invalid_request")
            if path == "/api/v1/packs":
                limit = query.get("limit", "20")
                if not limit.isascii() or not limit.isdecimal() or not 1 <= int(limit) <= 100:
                    return error(400, "invalid_request")
                cursor = query.get("cursor")
                if cursor is not None and not 1 <= len(cursor) <= 200:
                    return error(400, "invalid_cursor")
                result = self.packs.list_packs(cursor=cursor, limit=int(limit))
            else:
                if query:
                    return error(400, "invalid_request")
                parts = path.split("/")
                if (
                    len(parts) == 7
                    and parts[1:4] == ["api", "v1", "packs"]
                    and parts[5] == "versions"
                ):
                    result = self.packs.get_pack(unquote(parts[4]), unquote(parts[6]))
                elif len(parts) == 5 and parts[1:4] == ["api", "v1", "artifacts"]:
                    result = self.packs.get_artifact(unquote(parts[4]))
                else:
                    return error(404, "not_found")
            return Response(200, result, {"Cache-Control": "no-store"})
        except NotFound:
            return error(404, "not_found")
        except ValueError:
            return error(400, "invalid_cursor" if "cursor" in parsed.query else "invalid_request")
