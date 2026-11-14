"""Network restriction must fail closed without sending disallowed traffic."""

import subprocess
import sys


def test_feasibility_guard_blocks_external_dns_and_wrong_model_port():
    code = """
import socket
from experiments.acceptance.feasibility import restrict_network
counts = restrict_network("http://192.0.2.10:11434")
for address in [("192.0.2.10", 80), ("198.51.100.2", 11434)]:
    with socket.socket() as sock:
        try:
            sock.connect(address)
        except PermissionError:
            pass
        else:
            raise AssertionError("guard allowed disallowed destination")
try:
    socket.getaddrinfo("example.invalid", 443)
except PermissionError:
    pass
else:
    raise AssertionError("guard allowed DNS")
assert counts["blocked_connect"] == 3
assert counts["blocked_dns"] == 1
"""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, result.stderr
