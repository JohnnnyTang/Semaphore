"""Host-only W2 account and trusted-pack operations; durable games arrive in W3."""

import argparse
import getpass
import json
import sys
from contextlib import closing
from pathlib import Path

from .policy import INSTALL_MAX_BYTES, TransportPolicy
from .storage import connect, migrate


def bounded_read(path, maximum):
    with Path(path).open("rb") as stream:
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError("input exceeds operator budget")
    return data


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", help="Path to the hub SQLite database")
    parser.add_argument("--smoke", action="store_true", help="Run fake-only composition checks")
    parser.add_argument("--assets", default="hub-assets")
    parser.add_argument("--csrf-key", help="Host-restricted file containing 32 random bytes")
    parser.add_argument("--origin", default="http://localhost:8080")
    parser.add_argument("--disable-signup", action="store_true")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("migrate")
    bootstrap = commands.add_parser("bootstrap")
    bootstrap.add_argument("login")
    bootstrap.add_argument("display_name")
    reset = commands.add_parser("reset-password")
    reset.add_argument("account_id")
    install = commands.add_parser("install-pack")
    install.add_argument("manifest")
    install.add_argument("--owner", required=True)
    install.add_argument("--operator", required=True)
    install.add_argument("--rights-reference", required=True)
    install.add_argument("--accept-publication", action="store_true", required=True)
    artifact = commands.add_parser("accept-artifact")
    artifact.add_argument("pack_id")
    artifact.add_argument("version")
    artifact.add_argument("configuration", help="JSON initial_board/schedule/seed/generator_policy")
    artifact.add_argument("--operator", required=True)
    listener = commands.add_parser("serve-foundation")
    listener.add_argument("--port", type=int, default=8080)
    argv = list(sys.argv[1:] if argv is None else argv)
    # Preserve the original one-argument migration command despite subparser ambiguity.
    if len(argv) == 1 and not argv[0].startswith("-"):
        argv.append("migrate")
    if argv == ["--smoke"]:
        from .runtime_testing import smoke as runtime_smoke
        from .testing import smoke as repository_smoke

        runtime_smoke()
        print(f"Fake-only hub composition passed: {repository_smoke()}; no HTTP/model service.")
        return
    args = parser.parse_args(argv)
    if args.smoke:
        if args.database or args.command:
            parser.error("--smoke does not accept a database path or command")
        from .runtime_testing import smoke as runtime_smoke
        from .testing import smoke as repository_smoke

        runtime_smoke()
        print(f"Fake-only hub composition passed: {repository_smoke()}; no HTTP/model service.")
        return
    if not args.database:
        parser.error("provide a database path or --smoke")
    if args.command in {None, "migrate"}:
        from .host import exclusive_host

        with exclusive_host(args.database), closing(connect(args.database)) as connection:
            version = migrate(connection)
        print(f"Hub schema version {version}; use serve-foundation for W2 account/pack HTTP.")
        return
    if not args.csrf_key:
        parser.error("operator commands require --csrf-key")
    from .host import exclusive_host

    with exclusive_host(args.database, args.assets):
        run_operator(args, parser)


def run_operator(args, parser):
    from .host import prepare, serve

    embedder = None
    if args.command == "install-pack":
        from semaphore_core.embeddings import OllamaConfig, OllamaEmbedder, PinnedEmbedder

        embedder = PinnedEmbedder(OllamaEmbedder(OllamaConfig.from_env()))
    auth, packs = prepare(
        args.database,
        args.assets,
        TransportPolicy(args.origin, not args.disable_signup),
        args.csrf_key,
        embedder,
    )
    if args.command in {"bootstrap", "reset-password"}:
        password = getpass.getpass("New password: ")
        if password != getpass.getpass("Confirm password: "):
            parser.error("passwords do not match")
        if args.command == "bootstrap":
            print(auth.bootstrap(args.login, args.display_name, password))
        else:
            auth.reset_password(args.account_id, password)
            print("Password reset; sessions revoked.")
    elif args.command == "install-pack":
        result = packs.install(
            bounded_read(args.manifest, INSTALL_MAX_BYTES),
            owner_id=args.owner,
            operator_id=args.operator,
            rights_reference=args.rights_reference,
            accept=args.accept_publication,
        )
        print(json.dumps({"version_id": result.version_id, "report_id": result.report_id}))
    elif args.command == "accept-artifact":
        config = json.loads(bounded_read(args.configuration, INSTALL_MAX_BYTES))
        if not isinstance(config, dict) or set(config) != {
            "initial_board",
            "schedule",
            "seed",
            "generator_policy",
        }:
            parser.error("configuration must contain exactly the four documented fields")
        result = packs.accept_casual_artifact(
            args.pack_id, args.version, operator_id=args.operator, **config
        )
        print(json.dumps({"artifact_id": result.artifact_id}))
    elif args.command == "serve-foundation":
        if not 1 <= args.port <= 65535:
            parser.error("port must be between 1 and 65535")
        serve(auth, packs, args.port)


if __name__ == "__main__":
    main()
