# Semaphore

A light, playful word-association arcade game for a room full of people.

Semaphore runs on one LAN server. Players use thin browser clients to send
clues, clear target words, and compete on shared leaderboards. Creators build
themed word packs with their own coding agents and a separate creator kit;
the hub independently verifies each pack before publication.

## Project status

Planning stage. The game, hub, and creator kit are not implemented yet.

- [Product handoff](Semaphore%20%E2%80%94%20Handoff.md)
- [Project plan](PROJECT_PLAN.md): stages, waves, and parallel worktree sessions,
  with only Stage 1 planned in detail.

## Planned scope

- English-language Arcade mode with server-authoritative gameplay.
- CPU-based semantic ranking, with no server-side LLM or runtime internet dependency.
- Lightweight local accounts, versioned packs, and shared leaderboards.
- A creator CLI and agent skill using the same verification core as the hub.
- A target of 6–8 simultaneous players on a small LAN server.

## Development

Implementation will follow the stage → wave → session structure in the project
plan. Parallel sessions use separate Git worktrees and integrate at wave
boundaries. Later stages are detailed as evidence emerges.

Installation and development commands will be added with the first runnable
implementation.

## License

Semaphore's original code and documentation are available under the
[MIT License](LICENSE).

Third-party dependencies, embedding models, datasets, and separately licensed
word packs retain their own licenses. The repository's MIT license does not
relicense those materials.
