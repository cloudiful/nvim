#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE="${NVIM_BUNDLE_STAGE:?NVIM_BUNDLE_STAGE is required}"
source "$ROOT/scripts/nvim_paths.sh"

NVIM_CONFIG_HOME="$(nvim_native_path "$STAGE/.build/config")"
NVIM_DATA_HOME="$(nvim_native_path "$STAGE/.data")"
NVIM_SOURCE_ROOT="$(nvim_native_path "$ROOT")"
FETCH_SCRIPT="$(nvim_native_path "$ROOT/scripts/fetch_plugins.lua")"

mkdir -p "$STAGE/.data" "$STAGE/runtime" "$STAGE/.build/config/nvim"

XDG_CONFIG_HOME="$NVIM_CONFIG_HOME" \
XDG_DATA_HOME="$NVIM_DATA_HOME" \
NVIM_APPNAME=nvim \
NVIM_SOURCE_ROOT="$NVIM_SOURCE_ROOT" \
nvim --headless -u "$FETCH_SCRIPT" -c 'qa!'

test -d "$STAGE/.data/nvim/site/pack/core/opt"
