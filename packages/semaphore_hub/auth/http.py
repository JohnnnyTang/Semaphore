"""Framework-neutral HTTP adapter. Pass raw header pairs to preserve duplicates."""

import json
from dataclasses import dataclass

from semaphore_hub import policy as p

from .service import AuthError


@dataclass(frozen=True)
class Response:
    status: int
    body: dict | bytes | None
    headers: dict


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


class AuthHttp:
    def __init__(self, service):
        self.service = service

    def cookie(self, token, expire=False):
        value = f"{p.SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Strict"
        if self.service.policy.secure_cookie:
            value += "; Secure"
        value += "; Max-Age=0" if expire else "; Max-Age=86400"
        return value

    def handle(self, method, path, headers, body=b"", peer=""):
        out = {"Cache-Control": "no-store"}
        try:
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
                    raise AuthError(400, "invalid_request")
                values[key] = value
            if not self.service.policy.accepts(
                host=values.get("host", ""),
                origin=values.get("origin"),
                mutation=method not in {"GET", "HEAD"},
            ):
                raise AuthError(403, "origin_denied")
            if len(body) > p.REQUEST_MAX_BYTES:
                raise AuthError(413, "body_too_large")
            token = None
            for part in values.get("cookie", "").split(";"):
                name, sep, value = part.strip().partition("=")
                if sep and name == p.SESSION_COOKIE:
                    if token is not None:
                        raise AuthError(400, "invalid_request")
                    token = value
            if method == "GET" and path == "/api/v1/config":
                return Response(
                    200,
                    {
                        "signup_enabled": self.service.policy.signup_enabled,
                        "clue_retention_days": 30,
                        "backup_retention_days": 30,
                    },
                    out,
                )
            if method == "GET" and path == "/api/v1/auth/session":
                return Response(200, self.service.session(token), out)
            if method == "POST" and path == "/api/v1/auth/logout":
                if body:
                    raise AuthError(400, "invalid_request")
                self.service.logout(token, values.get("x-csrf-token"))
                out["Set-Cookie"] = self.cookie("", True)
                return Response(204, None, out)
            if method == "POST" and path in {"/api/v1/auth/login", "/api/v1/auth/signup"}:
                if (
                    values.get("content-type", "").split(";", 1)[0].strip().lower()
                    != "application/json"
                ):
                    raise AuthError(400, "invalid_request")
                try:
                    data = json.loads(
                        body.decode("utf8"),
                        object_pairs_hook=object_pairs,
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
                    )
                    signup = path.endswith("/signup")
                    required = {"login_name", "password"} | ({"display_name"} if signup else set())
                    if (
                        not isinstance(data, dict)
                        or set(data) != required
                        or not all(isinstance(v, str) for v in data.values())
                    ):
                        raise ValueError()
                except (ValueError, UnicodeError, RecursionError):
                    raise AuthError(400, "invalid_request") from None
                token, result = self.service.credentials(
                    data["login_name"], data["password"], peer, data.get("display_name"), token
                )
                out["Set-Cookie"] = self.cookie(token)
                return Response(201 if signup else 200, result, out)
            raise AuthError(404, "not_found")
        except AuthError as error:
            if error.retry_after:
                out["Retry-After"] = str(error.retry_after)
            return Response(
                error.status, {"code": error.code, "message": error.code.replace("_", " ")}, out
            )
