# Portable Neovim Config

This is a Neovim 0.12 configuration packaged with its plugins, Tree-sitter
parsers, queries, and blink.cmp native fuzzy matcher.

Release archives are offline bundles for Linux glibc x86_64/aarch64, macOS
arm64, and Windows x86_64. Extract an archive as the `nvim` directory under
your Neovim configuration directory. The archive does not include the
Neovim executable.

Each target has two profiles:

- `core` is the existing lightweight archive. Its name and contents remain
  compatible and it contains no formatter or LSP assets.
- `full` adds the target-compatible tools and `tool-manifest.json`. The
  archive name ends in `-full.tar.zst`.

Use `<leader>fm` for formatting. The resolver checks project tools, `mise`,
and `PATH` before using tools from a full bundle. The manifest reports every
tool as `bundled`, `external`, or `unsupported`; it never hides a platform
difference.

| Target | Bundled in `full` | External | Unsupported |
| --- | --- | --- | --- |
| Linux x86_64 gnu | `stylua`, `rustfmt`, `gofmt`, `shfmt`, `rust-analyzer`, `tombi` | Node, Prettier, Prettierd, Node-based LSPs, Java/Nushell/Hyprland tools | LuaLS |
| Linux aarch64 gnu | `stylua`, `rustfmt`, `gofmt`, `shfmt`, `tombi` | Node, Prettier, Prettierd, Node-based LSPs, Java/Nushell/Hyprland tools | LuaLS, rust-analyzer |
| macOS arm64 | All listed formatter/LSP assets, including Node, Prettier, Prettierd, LuaLS, rust-analyzer, Tombi, vtsls, and Vue LSP | Java/Nushell/Hyprland tools | None of the listed assets |
| Windows x86_64 | All listed formatter/LSP assets, including Node, Prettier, Prettierd, LuaLS, rust-analyzer, Tombi, vtsls, and Vue LSP | Java/Nushell/Hyprland tools | None of the listed assets |

The `*-gnu` bundles target glibc hosts. The release workflow also builds
`*-musl` bundles for musl-based hosts such as Alpine; the release table above
shows the tool support shared by both Linux variants.

Java support still requires `jdtls`, Java 21 or newer, and Maven or Gradle
project tooling. The full bundle does not include those project dependencies.
