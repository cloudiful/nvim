# Build Tooling

The bundle builder uses Python 3.14 and `uv`. Runtime dependencies remain in
the standard library; the build also requires Neovim, Git, Rust, Zig on Linux
targets, and `tar`/`zstd`.

Install the host tools and build either profile with:

```sh
uv sync --locked
uv run nvim-bundle install-nvim --version 0.12.4
uv run nvim-bundle install-tree-sitter --version 0.26.11
uv run nvim-bundle package --target macos-arm64 --profile core
uv run nvim-bundle package --target macos-arm64 --profile full
```

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

Java project support additionally requires an external `jdtls`, Java 21 or
newer, and Maven or Gradle project tooling.
