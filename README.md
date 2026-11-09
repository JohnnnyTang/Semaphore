# Semaphore

A light, playful word-association arcade game for a room full of people.

Semaphore runs on one LAN server. Players use thin browser clients to send
clues, clear target words, and compete on shared leaderboards. Creators build
themed word packs with their own coding agents and a separate creator kit;
the hub independently verifies each pack before publication.

## Project status

Stage 1, Wave 2: the semantic harness, gameplay specification and platform contract
drafts are integrated for review. Qwen3-Embedding 4B is selected for development
through a LAN Ollama server. Its adapter, offline tests and evaluation runner are
implemented; real model measurements await the operator's endpoint.
The game, hub, and creator kit are not implemented yet.
The repository provides synthetic fixtures, draft validation tools, a provisional
ranker interface, and automated checks.

- [Product handoff](Semaphore%20%E2%80%94%20Handoff.md)
- [Project plan](PROJECT_PLAN.md): stages, waves, and parallel worktree sessions,
  with only Stage 1 planned in detail.
- [Wave 1 evidence](docs/stages/s1-w1-baseline.md),
  [Wave 2 session briefs](docs/stages/s1-w2-session-briefs.md) and
  [Wave 2 progress](docs/stages/s1-w2-evidence-and-contracts.md).

## Planned scope

- English-language Arcade mode with server-authoritative gameplay.
- Server-side semantic ranking using LAN Ollama during development, with no
  generative LLM or runtime internet dependency. Release hardware remains unvalidated.
- Lightweight local accounts, versioned packs, and shared leaderboards.
- A creator CLI and agent skill using the same verification core as the hub.
- A target of 6–8 simultaneous players on a small LAN server.

## Development

Implementation will follow the stage → wave → session structure in the project
plan. Parallel sessions use separate Git worktrees and integrate at wave
boundaries. Later stages are detailed as evidence emerges.

Use Python 3.12 and [uv](https://docs.astral.sh/uv/). From the repository root:

```sh
uv sync --locked --group dev
uv run --no-sync ruff check .
uv run --no-sync ruff format --check .
uv run --no-sync pytest
uv build --no-build-isolation
```

For offline validation and the eventual LAN connectivity check, see the
[Ollama runner instructions](experiments/model_eval/README.md) and
[development decision](docs/decisions/0002-lan-ollama-development.md).

The lock file records the development dependencies. Initial installation needs
access to Python packages; the smoke checks use synthetic data and require no
model download or external network service. The fake ranker supplies deterministic test
results, not semantic quality or performance evidence.

GitHub Actions checks pull requests and pushes to `main` and `codex/**` branches.
Keep the checks green before integration; see the workflow files in
[`.github/workflows`](.github/workflows) for the exact jobs. Dependency update
proposals are configured in [`.github/dependabot.yml`](.github/dependabot.yml).
See the [automation notes](.github/README.md) for pin maintenance and GitHub settings.

Wave 2's semantic, gameplay and platform-contract sessions used isolated
worktrees from the same merged commit. Wave 3 will reconcile their evidence and
drafts before gameplay implementation begins. Historical CPU model experiments opt in with
`uv sync --locked --group dev --group model-eval`; model assets stay out of Git.

## License

Semaphore's original code and documentation are available under the
[MIT License](LICENSE).

Third-party dependencies, embedding models, datasets, and separately licensed
word packs retain their own licenses. The repository's MIT license does not
relicense those materials.
