"""Game routes for an already authenticated, Origin/CSRF-checked principal.

The host must apply those transport checks before calling this adapter.
"""

from urllib.parse import parse_qsl, unquote, urlsplit

from semaphore_core._manifest import parse
from semaphore_hub.auth import Response
from semaphore_hub.http import error
from semaphore_hub.policy import REQUEST_MAX_BYTES
from semaphore_hub.repositories import Conflict, NotFound

from .service import GameError


class GamesHttp:
    def __init__(self, games, results):
        self.games, self.results = games, results

    def handle(self, principal, method, target, body=b""):
        if principal is None:
            return error(401, "unauthenticated")
        if len(body) > REQUEST_MAX_BYTES:
            return error(413, "body_too_large")
        parsed = None
        try:
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or parsed.fragment:
                raise ValueError()
            parts = [unquote(p) for p in parsed.path.split("/")]
            if parts[:3] != ["", "api", "v1"]:
                raise NotFound()
            player = principal.account_id
            status = 200
            if method == "GET" and (
                parts[3:] == ["history"] or len(parts) == 5 and parts[3] == "boards"
            ):
                if body:
                    raise ValueError()
                pairs = parse_qsl(
                    parsed.query, keep_blank_values=True, strict_parsing=True, max_num_fields=2
                )
                query = dict(pairs)
                if len(query) != len(pairs) or set(query) - {"limit", "cursor"}:
                    raise ValueError()
                limit = query.get("limit", "20")
                if not limit.isascii() or not limit.isdecimal():
                    raise ValueError()
                args = dict(cursor=query.get("cursor"), limit=int(limit))
                result = (
                    self.results.history(player, **args)
                    if parts[3] == "history"
                    else self.results.board(parts[4], **args)
                )
            else:
                if parsed.query:
                    raise ValueError()
                if method == "GET" and body:
                    raise ValueError()
                if parts[3:] == ["games"] and method == "POST":
                    result = self.games.create(player, parse(body))
                    status = 201
                elif parts[3:] == ["games", "current"] and method == "GET":
                    result = self.games.current(player)
                    if result is None:
                        raise NotFound()
                elif len(parts) >= 5 and parts[3] == "games":
                    gid = parts[4]
                    if len(parts) == 5 and method == "GET":
                        result = self.games.get(player, gid)
                    elif len(parts) == 6 and parts[5] == "commands" and method == "POST":
                        result = self.games.command(player, gid, parse(body))
                        status = 202 if result["receipt"]["outcome"] == "pending" else 200
                    elif len(parts) == 6 and parts[5] == "quit" and method == "POST":
                        if body and parse(body) != {}:
                            raise ValueError()
                        result = self.games.quit(player, gid)
                    elif len(parts) == 7 and parts[5] == "receipts" and method == "GET":
                        result = self.games.receipt(player, gid, parts[6])
                    else:
                        raise NotFound()
                else:
                    raise NotFound()
            return Response(status, result, {"Cache-Control": "no-store"})
        except GameError as exc:
            return error(exc.status, exc.code)
        except NotFound:
            return error(404, "not_found")
        except Conflict:
            return error(503, "unavailable")
        except (ValueError, TypeError, RecursionError):
            return error(
                400, "invalid_cursor" if parsed is not None and parsed.query else "invalid_request"
            )
