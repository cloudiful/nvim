# Build Tooling

The bundle builder uses Python 3.14 and `uv`. Runtime dependencies remain in
the standard library; the build also requires Neovim, Git, Rust, Zig on Linux
targets, and `tar`/`zstd`.

Install the host tools and build either profile with:

```sh
uv sync --locked
uv run nvim-bundle install-nvim
uv run nvim-bundle install-tree-sitter --version 0.26.11
uv run nvim-bundle package --target macos-arm64 --profile core
uv run nvim-bundle package --target macos-arm64 --profile full
```

The pinned Neovim default in `src/nvim_bundle/models.py` is authoritative;
do not pass `--version` to `install-nvim` unless testing another version.

Supported targets are `linux-x86_64-musl`, `linux-aarch64-musl`,
`macos-arm64`, and `windows-x86_64`. `core` remains the default profile and
keeps its existing archive name. `full` adds `-full` to the archive name and
contains `tool-manifest.json`.

The full profile bundles `stylua`, `rustfmt`, `gofmt`, `shfmt`, Prettier,
Prettierd, LuaLS, rust-analyzer, Tombi, and the configured Docker, JSON, YAML,
CSS, Bash, vtsls, and Vue language servers whenever a verified asset exists
for the target. Node, Prettier, Prettierd, and Node-based LSPs are bundled on
macOS arm64 and Windows x86_64. Linux musl releases declare those tools as
`external`; LuaLS and Linux aarch64 rust-analyzer are currently
`unsupported`. Java `jdtls`, Java 21+, Maven/Gradle, Nushell LSP, and Hyprland
LSP remain `external` on every target.

Run the Python tests with:

```sh
uv run --locked python -m unittest discover -s tests -v
```

## Tool Asset Updates

Tool versions, URLs, and SHA-256 values are checked in to
`build/tool-assets.json`. To upgrade a tool, update its version and every
target asset, calculate the checksum from the exact downloaded archive, and
update the matching manifest definition in `src/nvim_bundle/tools.py`.
Run the unit tests and build the affected target with an isolated `PATH`.
CI must pass the formatter version/fixture checks and LSP initialize/exit
handshakes before a tool changes from `unsupported` to `bundled`.

## Stable Pin Updates

Pinned builds use `DEFAULT_NVIM_VERSION` plus four `NVIM_ASSETS` checksums in
`src/nvim_bundle/models.py` and exact commits in `nvim-pack-lock.json`.
Refresh them with:

```sh
uv run --locked nvim-bundle update-pins
uv run --locked nvim-bundle update-pins --check
```

`--check` reports drift without writing (exit 0 in sync, exit 2 drift
available, exit 1 on failure). Repeated updates with unchanged upstream refs
produce no diff. Failures (network/rate limits, missing or malformed sha256,
unrecognized source, unrecognized range, invalid SHA) fail closed before any
pin write.

Policy: Neovim selects the newest non-prerelease release with official
`assets[].digest` values; plugins select the highest stable SemVer tag by
numeric ordering with prereleases rejected and annotated tags resolved to
their peeled commit. Plugins without stable tags track the default-branch
commit as an explicit development fallback, not a stable guarantee. Blink
stays on the existing 1.x range: the plugin rev and `DEFAULT_BLINK_VERSION`
move together to the same stable 1.x tag.

Automation runs weekly (Monday 03:00 UTC) and via workflow_dispatch in
`.github/workflows/update-pins.yaml`. It runs unit tests, updates pins,
verifies with the pinned Neovim and a plugin-fetch smoke test, then
creates/updates one PR on `automation/update-pins`; no changes means no
commit or PR. The workflow needs `contents: write` and `pull-requests: write`
and uses `GITHUB_TOKEN` with no new secret. Never auto-merge: a human reviews
digests and revisions before merging. This repo mirrors Forgejo to GitHub;
merge the authoritative change per the existing mirror setup and do not
invent a write-back to Forgejo. A bot PR opened with `GITHUB_TOKEN` does not
trigger further Actions runs.

Java project support additionally requires an external `jdtls`, Java 21 or
newer, and Maven or Gradle project tooling.
