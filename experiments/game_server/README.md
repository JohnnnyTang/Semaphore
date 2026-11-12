# Bounded W4 game experiment

From the repository root, with the frozen Ollama runtime configured via
`SEMAPHORE_OLLAMA_BASE_URL`:

```powershell
uv run python -m experiments.game_server --manifest fixtures/w3/calibration-authored.json --web-root . --host 0.0.0.0 --port 8000
```

Open `/web/index.html?transport=http`. The preloaded artifact ID is `default`;
select the same mode passed to `--mode` (casual by default). Both modes use a
finite, non-repeating manifest-order word sequence and six initial words. Event
mode retains fixed 5-second spawns and capacity 12. Default casual mode uses
capacity 20, a 5-second base interval, score-dependent acceleration and five-clear
streak sweeps/cascades; see `contracts/gameplay.md`. Its arrival times depend on
clears, so it does not provide the event mode's identical schedule across players.
The server refuses a changed full model fingerprint and never downloads weights.
A manifest exceeding the ten-minute schedule envelope fails startup; prepare a
smaller experimental manifest instead. This is an operator-created artifact,
not an upload or publication API. No production accounts or durable scores exist.

`--web-root` points at the repository root, with only `/web/` and
`/fixtures/protocol/` exposed. Assets and API share one origin. Game IDs are opaque
process-local capabilities. Restart loses all sessions. HTTP binds loopback unless
the operator explicitly supplies a LAN host. No TLS or production auth is supplied.

`GameService` is the independently callable transport binding: `request(method,
path, raw_bytes) -> (http_status, envelope)`. Inject a synchronous embedding provider
and monotonic clock for offline protocol/load tests. Public completion/score routes
are deliberately absent. There is one FIFO game inference thread, eight physically
outstanding requests, one outstanding request per game and a five-second logical
deadline. An uncancellable timed-out call retains its capacity slot until it
returns; stale results cannot score. Requests waiting past their deadlines skip
embedding. Exceptions never expose model input or upstream service bodies.

Verification uses `semaphore_core.verification.verify_pack` separately; it cannot
enter the gameplay queue. Background verification pressure should be generated
from a separate bounded executor by the W5 harness. It may contend at the model
service; this prototype promises no inference preemption or latency acceptance.

Limits: at most 128 retained games, 4096 command IDs per game, 16 KiB request
bodies, fifteen-minute terminal retention, process-lifetime expired-ID tombstones.
Reads/submits trigger time advancement and retention collection. No timer thread
is required for authority: the next observation drains every due event before
responding, and worker completion drains time before scoring the current board.
Human feel, real 1/4/8-player round trips, background pressure and the unmet 100 ms
latency target remain W5 evidence gates.
