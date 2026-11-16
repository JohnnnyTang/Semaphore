from pathlib import Path

import pytest

from semaphore_hub.auth import Response
from semaphore_hub.browser_assets import ASSETS, BrowserAssets


class Dispatcher:
    def handle(self, method, target, headers, body, peer):
        assert target == "/api/v1/config"
        return Response(200 if headers == [("Host", "localhost:8080")] else 403, {}, {})


def test_browser_assets_are_bounded_and_explicit(tmp_path):
    for name in ASSETS:
        (tmp_path / name).write_bytes(name.encode())
    (tmp_path / "private.key").write_bytes(b"never expose")
    assets = BrowserAssets(tmp_path)
    headers = [("Host", "localhost:8080")]
    assert (
        assets.handle(Dispatcher(), "GET", "/", headers).headers["Location"] == "/web/durable.html"
    )
    for name, kind in ASSETS.items():
        response = assets.handle(Dispatcher(), "GET", "/web/" + name, headers)
        assert response.body == name.encode()
        assert response.headers["Content-Type"] == kind
    for path in (
        "/web/../private.key",
        "/web/%2e%2e/private.key",
        "/web/private.key",
        "/private.key",
    ):
        assert assets.handle(Dispatcher(), "GET", path, headers).status == 404
    assert assets.handle(Dispatcher(), "GET", "/web/durable.html", []).status == 403
    assert assets.handle(Dispatcher(), "POST", "/web/durable.html", headers).status == 404
    assert assets.handle(Dispatcher(), "GET", "/api/v1/history", headers) is None


def test_repository_browser_imports_are_served():
    assets = BrowserAssets(Path("web"))
    assert b"durable-app.mjs" in assets.files["durable.html"][0]
    assert b"store.mjs" in assets.files["durable-client.mjs"][0]


def test_missing_browser_assets_fail_before_serving(tmp_path):
    with pytest.raises(FileNotFoundError):
        BrowserAssets(tmp_path)
