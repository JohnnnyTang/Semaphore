"""One fresh verification execution path; raw manifest arrives on stdin."""

import argparse
import copy
import hashlib
import json
import math
import sys

from experiments.acceptance.common import ROOT, load


class SyntheticEmbedder:
    """Text-only deterministic unit vectors; no test-set lookup or semantic quality claim."""

    def __init__(self):
        self.calls = 0

    def identity(self):
        self.calls += 1
        # Satisfies the pinned identity boundary for plumbing; this is explicitly fake.
        return copy.deepcopy(load(ROOT / "contracts/model-lock.json")["fingerprint"])

    def _embed(self, texts):
        self.calls += 1
        rows = []
        for text in texts:
            seed = hashlib.sha256(text.encode("utf-8")).digest()
            row = [float(seed[i % len(seed)]) - 127.5 for i in range(2560)]
            norm = math.sqrt(sum(v * v for v in row))
            rows.append([v / norm for v in row])
        return rows

    embed_entries = _embed
    embed_queries = _embed


class RecordingEmbedder:
    def __init__(self, delegate):
        self.delegate = delegate
        self.entries = {}
        self.queries = {}

    def identity(self):
        return self.delegate.identity()

    def embed_entries(self, texts):
        rows = self.delegate.embed_entries(texts)
        self.entries.update(zip(texts, rows, strict=True))
        return rows

    def embed_queries(self, texts):
        rows = self.delegate.embed_queries(texts)
        self.queries.update(zip(texts, rows, strict=True))
        return rows


def audit(value, recorder, backend):
    """Compare every sampled rank and ordered ID, not just aggregate report metrics."""
    from experiments.w3 import verification as reference

    if backend == "core":
        from semaphore_core import verification as core

        semantic_hash = core.manifest_hashes(value).semantic_hash
        value = value.manifest
    else:
        from fixtures.manifests.check_examples import projected_hash

        semantic_hash = projected_hash(value)
    entries = {e["id"]: recorder.entries[e.get("embed_text", e["text"])] for e in value["entries"]}
    output = []
    for entry in value["entries"]:
        target = entry["id"]
        for sample in range(5):
            if backend == "core":
                decoys = core.sample_decoys(semantic_hash, target, sample, list(entries.items()))
            else:
                decoys = reference.samples(semantic_hash, target, entries)[sample]
            for clue_index, clue in enumerate(value["test_set"][target]):
                query = recorder.queries[clue]
                candidates = [(i, entries[i]) for i in [target, *decoys]]
                if backend == "core":
                    ranked = core.rank_vectors(query, candidates)
                    ids = [item.entry_id for item in ranked]
                    scores = {item.entry_id: item.score for item in ranked}
                else:
                    scores = {i: reference.dot(query, v) for i, v in candidates}
                    ids = reference.order(scores)
                output.append(
                    {
                        "target": target,
                        "sample": sample,
                        "clue_index": clue_index,
                        "ordered_ids": ids,
                        "scores": scores,
                        "target_rank": ids.index(target) + 1,
                    }
                )
    return output


def execute(raw, backend, *, ollama_url=None, parse_only=False):
    if ollama_url:
        from semaphore_core.embeddings import OllamaConfig, OllamaEmbedder

        embedder = OllamaEmbedder(OllamaConfig(base_url=ollama_url))
    else:
        embedder = SyntheticEmbedder()
    recorder = RecordingEmbedder(embedder)
    try:
        if backend == "core":
            from semaphore_core.verification import parse_manifest, verify_pack

            value = parse_manifest(raw)
            report = None if parse_only else verify_pack(value, recorder, "experiment-arcade-v1")
        else:
            from experiments.w3.verification import manifest, measure

            value = manifest(raw)
            report = None if parse_only else measure(raw, recorder)[0]
    except ValueError as exc:
        code = getattr(exc, "code", str(exc))
        allowed = {
            "invalid_json",
            "body_too_large",
            "schema_invalid",
            "hygiene_invalid",
            "duplicate_entry",
            "test_coverage",
            "duplicate_clue",
            "illegal_clue",
        }
        if code not in allowed:
            raise RuntimeError("unexpected verifier failure") from None
        return {"status": "rejected", "code": code, "embedding_calls": embedder.calls}
    return {
        "status": "parsed" if parse_only else "measured",
        "report": report,
        "audit": [] if parse_only else audit(value, recorder, backend),
        "embedding_calls": getattr(embedder, "calls", None),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=["reference", "core"], required=True)
    parser.add_argument("--ollama-url")
    parser.add_argument("--parse-only", action="store_true")
    parser.add_argument("--manifest-path")
    args = parser.parse_args()
    # Leave the actual 8 MiB limit to the verifier, not this process wrapper.
    from pathlib import Path

    options = vars(args)
    path = options.pop("manifest_path")
    raw = Path(path).read_bytes() if path else sys.stdin.buffer.read()
    value = execute(raw, **options)
    print(json.dumps(value, allow_nan=False))


if __name__ == "__main__":
    main()
