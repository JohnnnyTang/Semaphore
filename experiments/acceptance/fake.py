"""Disposable HTTP fake for harness development; no actual engine or inference."""

import copy
import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from experiments.acceptance.common import ROOT, load
from jsonschema import Draft202012Validator


def fake_server():
    template = load(ROOT / "fixtures/protocol/bottom-three-target-only.json")["envelopes"][0]
    games = {}
    guard = threading.Lock()
    schemas = load(ROOT / "contracts/http.schema.json")["$defs"]

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, status, value):
            raw = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def handle_request(self):
            size = int(self.headers.get("Content-Length", 0))
            if size > 16384:
                return self.respond(400, {"code": "invalid_request", "message": "Invalid request"})
            try:
                value = json.loads(self.rfile.read(size)) if size else None
            except ValueError:
                return self.respond(400, {"code": "invalid_request", "message": "Invalid request"})
            route = self.path.removeprefix("/experiment/v1").strip("/").split("/")
            with guard:
                if route == ["games"] and self.command == "POST":
                    if not Draft202012Validator(schemas["create"]).is_valid(value):
                        return self.respond(400, {"code": "invalid_request", "message": "Invalid"})
                    game_id = uuid.uuid4().hex
                    frame = copy.deepcopy(template)
                    frame["snapshot"]["game_id"] = game_id
                    frame["snapshot"]["mode"] = value["mode"]
                    frame["snapshot"]["deadline_ms"] = 3600000
                    games[game_id] = {"frame": frame, "receipts": {}, "payloads": {}}
                    return self.respond(201, frame)
                if len(route) < 2 or route[1] not in games:
                    return self.respond(404, {"code": "not_found", "message": "Unknown game"})
                game = games[route[1]]
                frame = game["frame"]
                state = frame["snapshot"]
                frame["receipt"] = None
                frame["kind"] = "snapshot"
                if len(route) == 3 and route[2] == "commands":
                    if not Draft202012Validator(schemas["command"]).is_valid(value):
                        return self.respond(400, {"code": "invalid_request", "message": "Invalid"})
                    command_id = value["command_id"]
                    if command_id in game["payloads"]:
                        outcome = (
                            None if game["payloads"][command_id] == value else "command_conflict"
                        )
                    elif value["expected_revision"] != state["revision"]:
                        outcome = "stale_revision"
                    elif len(value["clue"]) > 120:
                        outcome = "clue_too_long"
                    else:
                        outcome = "miss"
                        state["revision"] += 2
                    receipt = (
                        {
                            "command_id": command_id,
                            "outcome": outcome,
                            "applied_revision": state["revision"],
                            "target": state["target"],
                            "target_rank": 2 if outcome == "miss" else None,
                            "ranked_board": state["board"] if outcome == "miss" else [],
                            "score_delta": 0,
                        }
                        if outcome
                        else copy.deepcopy(game["receipts"][command_id])
                    )
                    if command_id not in game["payloads"]:
                        game["payloads"][command_id] = value
                        game["receipts"][command_id] = copy.deepcopy(receipt)
                    frame["receipt"], frame["kind"] = receipt, "receipt"
                elif len(route) == 4 and route[2] == "receipts":
                    frame["receipt"] = game["receipts"].get(route[3])
                    if not frame["receipt"]:
                        return self.respond(
                            404, {"code": "receipt_not_found", "message": "Unknown"}
                        )
                    frame["kind"] = "receipt"
                elif len(route) == 3 and route[2] == "quit":
                    if state["status"] != "over":
                        state["status"], state["end_reason"] = "over", "interrupted"
                        state["revision"] += 1
                    frame["kind"] = "terminal"
                return self.respond(200, frame)

        do_GET = handle_request
        do_POST = handle_request

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
