"""Same-origin LAN HTTP binding. Run with python -m experiments.game_server."""

import argparse
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from semaphore_core.embeddings import OllamaConfig, OllamaEmbedder, PinnedEmbedder

from .artifacts import DEFAULT_MANIFEST, prepare_artifact
from .service import GameService, ProtocolError


class BoundedHTTPServer(ThreadingHTTPServer):
    """Bound slow clients as well as inference work; excess sockets close immediately."""

    def __init__(self, *args, **kwargs):
        self.connections = threading.BoundedSemaphore(32)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        if not self.connections.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.connections.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.connections.release()


def make_server(service, *, host="127.0.0.1", port=8000, web_root=None):
    root = Path(web_root).resolve() if web_root else None

    class Handler(SimpleHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def end_headers(self):
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; "
                "script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
                "form-action 'self'",
            )
            super().end_headers()

        def log_message(self, *_args):
            # Neither URL command IDs nor raw clues go to access logs.
            pass

        def _json(self, status, payload, headers=None):
            data = json.dumps(payload, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(data)

        def _dispatch(self):
            try:
                if self.headers.get("Origin"):
                    try:
                        origin = urlsplit(self.headers["Origin"])
                    except ValueError:
                        raise ProtocolError(400, "invalid_request") from None
                    if origin.scheme != "http" or origin.netloc != self.headers.get("Host"):
                        raise ProtocolError(400, "invalid_request")
                raw = b""
                if self.command == "POST":
                    if (
                        self.headers.get_content_type() != "application/json"
                        or len(self.headers.get_all("Content-Length", [])) != 1
                        or self.headers.get("Sec-Fetch-Site") == "cross-site"
                    ):
                        raise ProtocolError(400, "invalid_request")
                    if self.headers.get("Transfer-Encoding"):
                        raise ProtocolError(400, "invalid_request")
                    try:
                        length = int(self.headers.get("Content-Length", "0"))
                    except ValueError:
                        raise ProtocolError(400, "invalid_request") from None
                    if not 0 <= length <= 16384:
                        raise ProtocolError(400, "invalid_request")
                    raw = self.rfile.read(length)
                    if len(raw) != length:
                        raise ProtocolError(400, "invalid_request")
                status, payload = service.request(self.command, self.path, raw)
                self._json(status, payload, service.timing_headers(payload))
            except ProtocolError as exc:
                self._json(exc.status, dict(code=exc.code, message=exc.code.replace("_", " ")))
            except (OSError, TimeoutError):
                self.close_connection = True

        def do_POST(self):
            self._dispatch()

        def do_GET(self):
            if urlsplit(self.path).path.startswith("/experiment/"):
                self._dispatch()
                return
            path = unquote(urlsplit(self.path).path)
            if path in ("/", "/web/"):
                path = "/web/index.html"
            if root is None or not (
                path.startswith("/web/") or path.startswith("/fixtures/protocol/")
            ):
                self._json(404, dict(code="not_found", message="not found"))
                return
            mount = root / ("web" if path.startswith("/web/") else "fixtures/protocol")
            target = (root / path.lstrip("/")).resolve()
            if (
                not target.is_relative_to(mount)
                or not target.is_file()
                or any(part.startswith(".") for part in target.relative_to(root).parts)
                or target.suffix.lower()
                not in {".html", ".css", ".js", ".mjs", ".svg", ".json", ".webp", ".woff2"}
            ):
                self._json(404, dict(code="not_found", message="not found"))
                return
            data = target.read_bytes()
            self.send_response(200)
            content_type = (
                "text/javascript"
                if target.suffix.lower() in {".js", ".mjs"}
                else self.guess_type(str(target))
            )
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_HEAD(self):
            self._json(404, dict(code="not_found", message="not found"))

    return BoundedHTTPServer((host, port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--mode", choices=["casual", "event"], default="casual")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--web-root", type=Path)
    args = parser.parse_args()
    embedder = PinnedEmbedder(OllamaEmbedder(OllamaConfig.from_env()))
    artifact = prepare_artifact(args.manifest.read_bytes(), embedder, mode=args.mode)
    service = GameService({"default": artifact}, embedder)
    server = make_server(service, host=args.host, port=args.port, web_root=args.web_root)
    print("Experimental in-memory game service ready; artifact_id=default")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        service.close()


if __name__ == "__main__":
    main()
