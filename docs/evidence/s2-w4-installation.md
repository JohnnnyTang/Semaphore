# Stage 2 W4 installation acceptance

November 16, 2026 (Asia/Shanghai). Tested source baseline
`b7f686ad2c0c33a28761b2d84c00574e63ed5e61`; worker branch
`codex/s2-w4-install`. This records local dependency/package acceptance, not
release packaging or remote-model offline readiness.

## Results

| Check | Observed result |
| --- | --- |
| Fresh `uv sync --locked --group dev` | Passed: new environment and empty dedicated package cache; 20 packages installed, including actual dependency downloads |
| `uv build --no-build-isolation` | Passed: sdist built, then wheel built from sdist |
| Fresh installed environment operator/migration tests | 22 passed in 5.47 s |
| Second environment `uv sync --offline --locked --group dev` | Passed using the first install's dedicated cache |
| Independent wheel install with hashed locked runtime dependencies | Passed: 11 dependencies plus wheel, no editable source import |
| Wheel imports/resources/CLI outside checkout with `python -I` | Passed in both online-prepared and later offline wheel environments |
| Initial offline `uv pip install --require-hashes` after project sync | Failed: resolver reported `argon2-cffi` unavailable in cache |
| Offline wheel dependency install after online pip resolution populated cache | Passed in another new environment |

Host: Windows 10 Enterprise, version 10.0.19045, 64-bit. Tools: CPython 3.12.10, uv 0.8.4; build backend `uv_build==0.9.18`
from the lock. CI specifies uv 0.9.18, so this local result does not verify that
exact CI frontend version. Python itself was already installed; no fresh Python
runtime download or air-gapped machine bootstrap was tested. No model endpoint
was contacted.

The initial offline wheel failure shows that a successful locked project sync
alone did not provide all metadata needed by the separate pip-style resolver.
An online hashed dependency install populated what that resolver needed; only
then did its offline repeat pass. Do not advertise the uv cache as a portable
wheelhouse or a complete offline deployment bundle.

## Reproduce

Use unused paths below, from the checkout root. Each environment was absent before
its creation. All generated environments/caches/requirements stay under ignored
`data/`; distribution artifacts stay under ignored `dist/`.

```powershell
$env:UV_PROJECT_ENVIRONMENT = Join-Path (Get-Location) 'data/install-online'
$env:UV_CACHE_DIR = Join-Path (Get-Location) 'data/install-cache'
uv sync --locked --group dev
uv build --no-build-isolation
uv export --locked --no-dev --no-emit-project --format requirements-txt --output-file data/runtime-requirements.txt
data/install-online/Scripts/python.exe -m pytest -q tests/hub/operations/test_cli_acceptance.py tests/hub/contracts/test_foundation.py

$env:UV_PROJECT_ENVIRONMENT = Join-Path (Get-Location) 'data/install-offline'
uv sync --offline --locked --group dev
uv venv data/wheel-env --python 3.12 --offline
uv pip install --python data/wheel-env/Scripts/python.exe --require-hashes -r data/runtime-requirements.txt
uv pip install --offline --python data/wheel-env/Scripts/python.exe --no-deps dist/semaphore_core-0.0.1-py3-none-any.whl

uv venv data/wheel-offline --python 3.12 --offline
uv pip install --offline --python data/wheel-offline/Scripts/python.exe --require-hashes -r data/runtime-requirements.txt
uv pip install --offline --python data/wheel-offline/Scripts/python.exe --no-deps dist/semaphore_core-0.0.1-py3-none-any.whl
```

Run the installed smoke with each wheel interpreter from outside the checkout:

```powershell
$installedPython = Join-Path (Get-Location) 'data/wheel-env/Scripts/python.exe'
$smokeScript = Join-Path (Get-Location) 'experiments/durable_installation/installed_smoke.py'
Push-Location $env:TEMP
& $installedPython -I $smokeScript
Pop-Location
```

Repeat with `data/wheel-offline/Scripts/python.exe`. The script refuses module
imports outside the selected interpreter's environment. It imports core, hub,
durable host, browser serving, operations readiness and runtime; checks three
shipped JSON schemas, durable OpenAPI and the pinned model-lock resource; reads
both migration SQL files; migrates a fresh DB to schema v2 twice; and runs CLI
smoke, migration and `serve-durable --help` in isolated child processes. Help must
include `--web-root`. It requires no repository fixtures, model calls or source
package paths. Ruff lint/format pass for the script.

The 22 tests also exercise runbook commands through real CLI subprocesses:
`migrate`, `backup`, `cleanup`, `delete-clues`, `delete-account` and `restore`.
Bootstrap executes CLI main with only the interactive password prompt replaced;
see [operator evidence](s2-w4-operations.md). The documented browser command was
parser-checked here, not launched against a real model in this installation check.

## Artifact identity

| Artifact at tested baseline | SHA-256 |
| --- | --- |
| `uv.lock` | `d0a07dac57be45d58fbfc2094bf41c1972893be43fcb5bc71941ba63a9f600c4` |
| `semaphore_core-0.0.1-py3-none-any.whl` (102,897 bytes) | `a4cf6ee60c4bdcf6a36f4a0ff3ec478dcb2c99bfac94a94b8932187ea40cfd2d` |
| `semaphore_core-0.0.1.tar.gz` (78,208 bytes) | `149aa886818d0e08b11d9cd48c824097affae39e98ddb87c31a7de8e5ed006d2` |

These hashes identify the measured local build, not a guarantee that a later
source tree produces identical archives. No dependency or lockfile changed.

## Remaining boundary

The installed Python modules/resources and local cached install are verified.
The browser `web` directory remains separately supplied via `--web-root`; this
wheel is not a complete release bundle. This work does not prove a fully offline
model/assets startup, remote-host CPU/RAM support, LAN serving, human gameplay or
1/4/8-player model performance. Those inherited and W4 gates remain open.
