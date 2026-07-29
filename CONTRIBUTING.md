# Build Tooling

The bundle builder uses Python 3.14 and `uv`. Runtime dependencies remain in
the standard library; the build still requires Neovim, Git, Rust, Zig on Linux
targets, and `tar`/`zstd`.

Install the host tools and build a bundle with:

```sh
uv sync --locked
uv run nvim-bundle install-nvim --version 0.12.4
uv run nvim-bundle install-tree-sitter --version 0.26.11
uv run nvim-bundle package --target macos-arm64
```

Supported targets are `linux-x86_64-musl`, `linux-aarch64-musl`,
`macos-arm64`, and `windows-x86_64`. The output archive is written to
`.build/output` unless `--output-dir` is provided.

Run the Python tests with:

```sh
uv run python -m unittest discover -s tests -v
```

## Optional Runtime Tools

The core bundle does not contain formatter binaries or language servers.
Conform formats manually with `<leader>fm` when these commands are available
from the project environment, `mise`, or `PATH`:

- `stylua` for Lua
- `rustfmt` for Rust
- `gofmt` for Go
- `shfmt` for Bash and shell scripts
- `prettierd` or `prettier` for JavaScript, TypeScript, Vue, JSON, YAML, and Markdown

Java uses the full `nvim-jdtls` mode. Install a `jdtls` executable, Java 21 or
newer, and Maven or Gradle project tooling. Java debug and test integrations
are intentionally not included.
