"""Windows local-process resources and Python network-restricted real-model startup.

Does not isolate the remote model host or restart its model. No synthetic fallback.
"""

import argparse
import ctypes
import hashlib
import ipaddress
import json
import os
import platform
import socket
import sys
import threading
import time
from collections import Counter
from ctypes import wintypes
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit


class Memory(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
        (name, ctypes.c_size_t)
        for name in (
            "PeakWorkingSetSize",
            "WorkingSetSize",
            "QuotaPeakPagedPoolUsage",
            "QuotaPagedPoolUsage",
            "QuotaPeakNonPagedPoolUsage",
            "QuotaNonPagedPoolUsage",
            "PagefileUsage",
            "PeakPagefileUsage",
            "PrivateUsage",
        )
    ]


def resources():
    if sys.platform != "win32":
        raise RuntimeError("Windows resource collector required")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Memory), wintypes.DWORD]
    memory = Memory()
    memory.cb = ctypes.sizeof(memory)
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(memory), memory.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return dict(
        cpu_seconds=time.process_time(),
        working_set_bytes=memory.WorkingSetSize,
        peak_working_set_bytes=memory.PeakWorkingSetSize,
        private_bytes=memory.PrivateUsage,
    )


def restrict_network(origin):
    parts = urlsplit(origin)
    host = str(ipaddress.ip_address(parts.hostname))  # literal operator-provided IP only
    endpoint = (host, parts.port or (443 if parts.scheme == "https" else 80))
    connections = Counter()

    def audit(event, args):
        if event == "socket.getaddrinfo":
            if args[0] not in {host, "127.0.0.1", "::1"}:
                connections["blocked_dns"] += 1
                raise PermissionError("network guard")
        if event == "socket.connect":
            address = args[1]
            if address[0] in {"127.0.0.1", "::1"}:
                connections["loopback"] += 1
            elif tuple(address[:2]) == endpoint:
                connections["configured_model"] += 1
            else:
                connections["blocked_connect"] += 1
                raise PermissionError("network guard")

    sys.addaudithook(audit)
    with socket.socket() as check:
        try:
            check.connect(("203.0.113.1", 9))
        except PermissionError:
            pass
        else:
            raise RuntimeError("guard failed")
    return connections


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    report = dict(
        started_utc=datetime.now(UTC).isoformat(),
        python=platform.python_version(),
        platform=platform.platform(),
        logical_cpus=os.cpu_count(),
        offline_scope="Python process sockets: loopback + configured model IP/port only",
        remote_host_isolation_verified=False,
        model_cold_start_verified=False,
        acceptance_established=False,
        process_start_resources=resources(),
    )
    connections = restrict_network(os.environ["SEMAPHORE_OLLAMA_BASE_URL"])
    service = server = None
    sampler_stop = threading.Event()
    samples = []

    def sample():
        while not sampler_stop.wait(0.1):
            samples.append(dict(elapsed_seconds=time.perf_counter() - start, **resources()))

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()

    def save(name, value):
        (args.output_dir / name).write_text(
            json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )

    try:
        from urllib.request import ProxyHandler, build_opener

        from experiments.acceptance.load import HTTPTransport, player
        from experiments.game_server.__main__ import make_server
        from experiments.game_server.artifacts import prepare_artifact
        from experiments.game_server.service import GameService

        from semaphore_core.embeddings import OllamaConfig, OllamaEmbedder, PinnedEmbedder
        from semaphore_core.verification import parse_manifest, verify_pack

        provider = OllamaEmbedder(OllamaConfig.from_env())
        embedder = PinnedEmbedder(provider)
        report["model_identity"] = embedder.identity()
        report["model_inventory_before"] = provider._request("/api/ps")
        raw = args.manifest.read_bytes()
        report["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
        artifact = prepare_artifact(raw, embedder)
        service = GameService({"default": artifact}, embedder)
        root = Path(__file__).resolve().parents[2]
        server = make_server(service, port=0, web_root=root)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        origin = f"http://127.0.0.1:{server.server_port}"
        opener = build_opener(ProxyHandler({}))
        with opener.open(origin, timeout=10) as response:
            report["index_http_status"] = response.status
            report["index_bytes"] = len(response.read())
        report["startup_seconds"] = time.perf_counter() - start
        print("Real pinned startup passed; measuring HTTP gameplay", flush=True)
        import concurrent.futures

        report["gameplay"] = []
        for count in (1, 4, 8):
            gate = threading.Barrier(count)
            records = [[] for _ in range(count)]
            errors = []
            group_start = time.perf_counter()
            with concurrent.futures.ThreadPoolExecutor(max_workers=count) as pool:
                futures = [
                    pool.submit(
                        player,
                        HTTPTransport(origin),
                        "default",
                        "casual",
                        3,
                        gate,
                        records=records[n],
                    )
                    for n in range(count)
                ]
                for future in futures:
                    try:
                        future.result()
                    except Exception as exc:
                        errors.append(type(exc).__name__)
            report["gameplay"].append(
                dict(
                    players=count,
                    rounds_per_player=3,
                    elapsed_seconds=time.perf_counter() - group_start,
                    records=records,
                    errors=errors,
                )
            )
            print(f"Completed {count}-player probe", flush=True)
        print("Running pilot semantic verification", flush=True)
        verification_start = time.perf_counter()
        quality = verify_pack(parse_manifest(raw), embedder, "experiment-arcade-v1")
        save("semantic.json", quality)
        report["verification_seconds"] = time.perf_counter() - verification_start
        report["model_residency_after"] = provider.running_model()
        report["probe_completed"] = True
    except Exception as exc:
        report["probe_completed"] = False
        report["failure_type"] = type(exc).__name__
        print(f"Probe failed: {type(exc).__name__}", flush=True)
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if service is not None:
            service.close()
        sampler_stop.set()
        sampler.join()
        report["elapsed_seconds"] = time.perf_counter() - start
        report["process_end_resources"] = resources()
        report["network_counts"] = dict(connections)
        report["network_self_test_blocks"] = 1
        report["resource_sample_interval_seconds"] = 0.1
        save("resources.json", samples)
        save("startup.json", report)
    return 0 if report["probe_completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
