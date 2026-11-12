"""Serve the experiment HTTP binding with controlled vectors for browser QA."""

import json
from dataclasses import replace
from pathlib import Path

from experiments.acceptance.verify_worker import SyntheticEmbedder
from experiments.game_server.__main__ import make_server
from experiments.game_server.artifacts import prepare_artifact
from experiments.game_server.service import GameService

from semaphore_core.verification import normalize

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "fixtures/w3/calibration-authored.json"


class AuthoredClueEmbedder(SyntheticEmbedder):
    """Map authored clues to their corresponding entry's unit vector."""

    def __init__(self, manifest):
        super().__init__()
        entries = manifest["entries"]
        self.positions = {entry["embed_text"]: index for index, entry in enumerate(entries)}
        self.clues = {
            normalize(clue): index
            for index, entry in enumerate(entries)
            for clue in manifest["test_set"][entry["id"]]
        }

    def _vector(self, position):
        row = [0.0] * 2560
        row[position] = 1.0
        return row

    def embed_entries(self, texts):
        return [self._vector(self.positions[text]) for text in texts]

    def embed_queries(self, texts):
        return [self._vector(self.clues[text]) for text in texts]


def main():
    raw = MANIFEST.read_bytes()
    provider = AuthoredClueEmbedder(json.loads(raw))
    artifact, vectors = prepare_artifact(raw, provider)
    # Three normal arrivals make the browser's automatic end test quick.
    artifact = replace(artifact, schedule=artifact.schedule[:3], deadline_ms=20000)
    service = GameService({"default": (artifact, vectors)}, provider)
    try:
        with make_server(service, port=18739, web_root=ROOT) as server:
            print("Synthetic browser test service listening on 127.0.0.1:18739", flush=True)
            server.serve_forever()
    finally:
        service.close()


if __name__ == "__main__":
    main()
