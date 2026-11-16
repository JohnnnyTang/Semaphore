"""Reproducible frozen Argon2 profile benchmark; synthetic secrets only."""

import concurrent.futures
import ctypes
import importlib.metadata
import json
import platform
import statistics
import time

from argon2 import PasswordHasher, Type
from argon2.exceptions import VerifyMismatchError


class Counters(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong)] + [
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
        )
    ]


def main():
    hasher = PasswordHasher(
        time_cost=3, memory_cost=65536, parallelism=1, hash_len=32, salt_len=16, type=Type.ID
    )
    password = "synthetic benchmark credential"
    hashed = hasher.hash(password)

    def operation(kind):
        start = time.perf_counter()
        if kind == "hash":
            hasher.hash(password)
        else:
            try:
                assert hasher.verify(
                    hashed, password if kind == "verify" else "wrong synthetic password"
                )
                assert kind == "verify"
            except VerifyMismatchError:
                assert kind == "wrong"
        return (time.perf_counter() - start) * 1000

    result = {
        "os": platform.platform(),
        "cpu": platform.processor(),
        "argon2_cffi": importlib.metadata.version("argon2-cffi"),
        "samples": {},
    }
    for kind in ["hash", "verify", "wrong"]:
        for _ in range(5):
            operation(kind)
        serial = [operation(kind) for _ in range(30)]
        paired = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            for _ in range(30):
                paired.extend(pool.map(operation, [kind, kind]))
        for label, values in [("serial", serial), ("paired", paired)]:
            result["samples"][kind + "_" + label] = {
                "n": len(values),
                "p50_ms": round(statistics.median(values), 2),
                "p95_ms": round(sorted(values)[int(0.95 * len(values)) - 1], 2),
            }
    counts = Counters()
    counts.cb = ctypes.sizeof(counts)
    kernel = ctypes.WinDLL("kernel32")
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    psapi = ctypes.WinDLL("psapi")
    psapi.GetProcessMemoryInfo.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(Counters),
        ctypes.c_ulong,
    ]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counts), counts.cb):
        raise ctypes.WinError()
    result["process_peak_rss_bytes"] = counts.PeakWorkingSetSize
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
