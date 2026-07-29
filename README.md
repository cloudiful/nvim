# Portable Neovim Config

This is a Neovim 0.12 configuration packaged with its plugins, Tree-sitter
parsers, queries, and blink.cmp native fuzzy matcher.

The release archives are offline bundles. Linux archives target musl and are
provided for x86_64 and aarch64. macOS arm64 and Windows x86_64 archives are
also available.

Extract an archive as the `nvim` directory under your Neovim configuration
directory. The bundle does not include the Neovim executable or language
servers.

Formatting is manual through `<leader>fm`. Conform uses formatter commands
already available through the project environment, `mise`, or `PATH`, and
falls back to the attached LSP when no formatter is installed. Formatter
binaries and language servers are intentionally outside the core offline
bundle. Java project support additionally requires `jdtls`, Java 21 or newer,
and Maven or Gradle project tooling.
