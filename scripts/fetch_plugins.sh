#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE="${NVIM_BUNDLE_STAGE:?NVIM_BUNDLE_STAGE is required}"

mkdir -p "$STAGE/.data" "$STAGE/runtime" "$STAGE/.build/config/nvim"
cp "$ROOT/nvim-pack-lock.json" "$STAGE/.build/config/nvim/nvim-pack-lock.json"

XDG_CONFIG_HOME="$STAGE/.build/config" \
XDG_DATA_HOME="$STAGE/.data" \
NVIM_APPNAME=nvim \
NVIM_SOURCE_ROOT="$ROOT" \
nvim --headless -u "$ROOT/scripts/fetch_plugins.lua" -c 'qa!'

test -d "$STAGE/.data/nvim/site/pack/core/opt"
