#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE="${NVIM_BUNDLE_STAGE:?NVIM_BUNDLE_STAGE is required}"
source "$ROOT/scripts/nvim_paths.sh"
TS_DIR="$STAGE/.build/nvim-treesitter"
TS_REV="$(tr -d '[:space:]' < "$ROOT/build/nvim-treesitter.rev")"
TS_SOURCE="${TREESITTER_SOURCE:-https://github.com/nvim-treesitter/nvim-treesitter.git}"

NVIM_CACHE_HOME="$(nvim_native_path "$STAGE/.build/cache")"
NVIM_PLUGIN_DIR="$(nvim_native_path "$TS_DIR")"
NVIM_INSTALL_DIR="$(nvim_native_path "$STAGE/runtime")"
NVIM_LANGUAGES_FILE="$(nvim_native_path "$ROOT/build/treesitter-languages.txt")"
BUILD_SCRIPT="$(nvim_native_path "$ROOT/scripts/build_treesitter.lua")"

mkdir -p "$STAGE/.build"
git clone --filter=blob:none --no-checkout "$TS_SOURCE" "$TS_DIR"
git -C "$TS_DIR" fetch --depth=1 origin "$TS_REV"
git -C "$TS_DIR" checkout --detach --quiet "$TS_REV"

mkdir -p "$STAGE/runtime/parser" "$STAGE/runtime/queries"
export XDG_CACHE_HOME="$NVIM_CACHE_HOME"
TREESITTER_PLUGIN_DIR="$NVIM_PLUGIN_DIR" \
TREESITTER_INSTALL_DIR="$NVIM_INSTALL_DIR" \
TREESITTER_LANGUAGES_FILE="$NVIM_LANGUAGES_FILE" \
TREESITTER_MAX_JOBS="${TREESITTER_MAX_JOBS:-}" \
nvim --headless -u NONE -l "$BUILD_SCRIPT"

if [[ "$NVIM_BUNDLE_TARGET" == linux-*-musl ]]; then
  TREESITTER_LANGUAGES_FILE="$ROOT/build/treesitter-languages.txt" \
  NVIM_BUNDLE_STAGE="$STAGE" \
  NVIM_BUNDLE_TARGET="$NVIM_BUNDLE_TARGET" \
  "$ROOT/scripts/cross_compile_treesitter.sh"
fi
