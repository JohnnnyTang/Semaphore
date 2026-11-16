"""Offline schema preparation only; no production service is implied."""

import argparse
from contextlib import closing

from .storage import connect, migrate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", nargs="?", help="Path to the hub SQLite database")
    parser.add_argument("--smoke", action="store_true", help="Run fake-only composition checks")
    args = parser.parse_args()
    if args.smoke:
        if args.database:
            parser.error("--smoke does not accept a database path")
        from .runtime_testing import smoke as runtime_smoke
        from .testing import smoke as repository_smoke

        runtime_smoke()
        summary = repository_smoke()
        print(f"Fake-only hub composition passed: {summary}; no HTTP/model service.")
        return
    if not args.database:
        parser.error("provide a database path or --smoke")
    with closing(connect(args.database)) as connection:
        version = migrate(connection)
    print(f"Hub schema version {version}; HTTP service is not implemented.")


if __name__ == "__main__":
    main()
