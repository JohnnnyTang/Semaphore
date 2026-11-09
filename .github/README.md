# Repository automation

`CI` checks every pull request, pushes to `main` and `codex/**`, merge-queue
groups, and manual dispatches. It deliberately has no path filters so a required
check cannot remain pending after a documentation-only change. Jobs use read-only
repository permissions, checkout without persisted credentials, pinned action
commits, and bounded runtimes. No publishing credentials or repository secrets
are needed, including for fork pull requests.

The checks are:

- `Python quality`: locked development install, Ruff lint and formatting.
- `Tests and package (ubuntu-24.04)` and `Tests and package (windows-2025)`:
  locked development install, tests, source/wheel build, and a wheel import in an
  isolated environment. Python follows the repository's `.python-version`.
- `Workflow lint`: actionlint validates workflow syntax, expressions and shell
  commands. Its release archive is verified against a pinned SHA-256 digest
  before execution.

CI proves the scaffold works; it does not download embedding models or establish
semantic quality, game performance, offline deployment, or release readiness.

## Maintaining the pins

Dependabot opens weekly update pull requests for GitHub Actions and the root
`uv.lock` project. Updates still need review and passing checks; there is no
automatic merge. The uv executable version is pinned once in `ci.yml` as
`UV_VERSION`, independently of the setup action. Update that version after
checking local lock/sync/build compatibility. Dependabot does not update this
environment value or the actionlint release URL/checksum: review those pins
manually when updating the CI toolchain.

For actionlint, select an official release, verify the release checksum, then
update both the URL and digest together. To lint locally, run `actionlint` from
the repository root. The initial pins were checked against these sources:

- [Checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1)
- [setup-uv v10.3.3](https://github.com/astral-sh/setup-uv/releases/tag/v10.3.3)
- [actionlint v1.7.12](https://github.com/rhysd/actionlint/releases/tag/v1.7.12)
- [Supported Dependabot ecosystems](https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories)

## GitHub settings

The YAML files take effect when pushed. Dependabot version-update configuration
must land on the default branch. Branch protection or repository rulesets are
separate GitHub settings: after the first successful run, the check names above
can be required for `main`. Keep default workflow permissions read-only and
review workflow changes with the same care as application code. No deployment
or release workflow is included while the project is an experiment scaffold.
