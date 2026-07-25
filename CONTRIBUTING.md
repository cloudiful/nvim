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
