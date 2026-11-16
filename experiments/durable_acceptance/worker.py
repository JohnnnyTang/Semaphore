"""Persistent worker. Adapter stdout is never copied to evidence."""

import importlib
import json
import sys
import time
from pathlib import Path


def main():
    module, workspace = sys.argv[1:]
    root = Path(workspace)
    selected_fault = None

    def checkpoint(name):
        if name == selected_fault:
            marker = root / "checkpoint.tmp"
            marker.write_text(json.dumps({"checkpoint": name}))
            marker.replace(root / "checkpoint.json")
            while True:
                time.sleep(1)

    try:
        adapter = importlib.import_module(module).open_adapter(root, checkpoint)
        for line in sys.stdin:
            request = json.loads(line)
            selected_fault = request["fault"]
            result = adapter.execute(request["operation"], request["payload"])
            temporary = root / "result.tmp"
            temporary.write_text(json.dumps(result, allow_nan=False))
            temporary.replace(root / "result.json")
    except BaseException:
        (root / "failure.json").write_text('{"code":"adapter_failed"}')
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
