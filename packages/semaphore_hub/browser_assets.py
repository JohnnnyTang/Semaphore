"""Explicit same-origin browser assets; never expose arbitrary repository files."""

from pathlib import Path
from urllib.parse import urlsplit

from semaphore_hub.auth import Response
from semaphore_hub.http import error

ASSETS = {
    "durable.html": "text/html; charset=utf-8",
    "durable-app.mjs": "text/javascript; charset=utf-8",
    "durable-client.mjs": "text/javascript; charset=utf-8",
    "store.mjs": "text/javascript; charset=utf-8",
    "durable.css": "text/css; charset=utf-8",
    "styles.css": "text/css; charset=utf-8",
    "favicon.svg": "image/svg+xml",
}
MAX_ASSET_BYTES = 2 * 1024 * 1024


class BrowserAssets:
    def __init__(self, root):
        root = Path(root).resolve(strict=True)
        self.files = {}
        for name, content_type in ASSETS.items():
            path = root / name
            if path.resolve(strict=True).parent != root:
                raise ValueError("browser asset escapes configured directory")
            with path.open("rb") as stream:
                raw = stream.read(MAX_ASSET_BYTES + 1)
            if len(raw) > MAX_ASSET_BYTES:
                raise ValueError("browser asset exceeds size budget")
            self.files[name] = (raw, content_type)

    def handle(self, dispatcher, method, target, headers, body=b"", peer=""):
        # API handling, including malformed URLs, remains in the durable dispatcher.
        try:
            parsed = urlsplit(target)
        except ValueError:
            return error(400, "invalid_request")
        if parsed.path.startswith("/api/"):
            return None
        if parsed.scheme or parsed.netloc or parsed.fragment or parsed.query:
            return error(400, "invalid_request")
        if method != "GET" or body:
            return error(404, "not_found")
        # The public config route enforces the exact Host/Origin and duplicate headers
        # without requiring an account merely to load the sign-in page.
        guard = dispatcher.handle("GET", "/api/v1/config", headers, b"", peer)
        if guard.status != 200:
            return guard
        name = "durable.html" if parsed.path == "/" else parsed.path.removeprefix("/web/")
        if parsed.path != "/" and not parsed.path.startswith("/web/"):
            return error(404, "not_found")
        if name not in self.files:
            return error(404, "not_found")
        if parsed.path == "/":
            return Response(
                302, None, {"Location": "/web/durable.html", "Cache-Control": "no-store"}
            )
        raw, content_type = self.files[name]
        return Response(200, raw, {"Content-Type": content_type, "Cache-Control": "no-store"})
