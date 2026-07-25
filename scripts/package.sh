#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${NVIM_BUNDLE_TARGET:?NVIM_BUNDLE_TARGET is required}"
OUT_DIR="${NVIM_BUNDLE_OUTPUT_DIR:-$ROOT/.build/output}"
STAGE="${NVIM_BUNDLE_STAGE:-$ROOT/.build/bundle/nvim}"

rm -rf "$ROOT/.build/bundle" "$OUT_DIR"
mkdir -p "$STAGE" "$OUT_DIR"
cp "$ROOT/init.lua" "$ROOT/nvim-pack-lock.json" "$ROOT/README.md" "$STAGE/"
cp -R "$ROOT/lua" "$STAGE/lua"

NVIM_BUNDLE_STAGE="$STAGE" "$ROOT/scripts/fetch_plugins.sh"
NVIM_BUNDLE_STAGE="$STAGE" NVIM_BUNDLE_TARGET="$TARGET" "$ROOT/scripts/build_treesitter.sh"
NVIM_BUNDLE_STAGE="$STAGE" NVIM_BUNDLE_TARGET="$TARGET" "$ROOT/scripts/fetch_blink.sh"

find "$STAGE/.data/nvim/site/pack/core/opt" -type d -name .git -prune -exec rm -rf {} +
rm -rf "$STAGE/.build"

TREESITTER_SKIP_LOAD=0
if [[ "$TARGET" == linux-*-musl ]]; then
  TREESITTER_SKIP_LOAD=1
fi

XDG_CONFIG_HOME="$ROOT/.build/bundle" \
NVIM_APPNAME=nvim \
TREESITTER_LANGUAGES_FILE="$ROOT/build/treesitter-languages.txt" \
TREESITTER_SKIP_LOAD="$TREESITTER_SKIP_LOAD" \
nvim --headless -u "$STAGE/init.lua" -c "luafile $ROOT/scripts/verify_bundle.lua" -c 'qa!'

ARCHIVE="$OUT_DIR/nvim-config-$TARGET.tar.zst"
tar -C "$ROOT/.build/bundle" -cf - nvim \
  | zstd -T0 -19 -o "$ARCHIVE"
printf '%s\n' "$ARCHIVE"
