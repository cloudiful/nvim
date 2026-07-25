#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE="${NVIM_BUNDLE_STAGE:?NVIM_BUNDLE_STAGE is required}"
TS_DIR="$STAGE/.build/nvim-treesitter"
TS_REV="$(tr -d '[:space:]' < "$ROOT/build/nvim-treesitter.rev")"
TS_SOURCE="${TREESITTER_SOURCE:-https://github.com/nvim-treesitter/nvim-treesitter.git}"

mkdir -p "$STAGE/.build"
git clone --filter=blob:none --no-checkout "$TS_SOURCE" "$TS_DIR"
git -C "$TS_DIR" fetch --depth=1 origin "$TS_REV"
git -C "$TS_DIR" checkout --detach --quiet "$TS_REV"

mkdir -p "$STAGE/runtime/parser" "$STAGE/runtime/queries"
TREESITTER_PLUGIN_DIR="$TS_DIR" \
TREESITTER_INSTALL_DIR="$STAGE/runtime" \
TREESITTER_LANGUAGES_FILE="$ROOT/build/treesitter-languages.txt" \
TREESITTER_MAX_JOBS="${TREESITTER_MAX_JOBS:-}" \
nvim --headless -u NONE -l "$ROOT/scripts/build_treesitter.lua"
