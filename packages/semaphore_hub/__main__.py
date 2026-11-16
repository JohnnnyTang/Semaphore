"""Offline schema preparation only; no production service is implied."""

import argparse
from contextlib import closing

from .storage import connect, migrate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", help="Path to the hub SQLite database")
    args = parser.parse_args()
    with closing(connect(args.database)) as connection:
        version = migrate(connection)
    print(f"Hub schema version {version}; HTTP service is not implemented.")


if __name__ == "__main__":
    main()
