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

if XDG_CONFIG_HOME="$NVIM_CONFIG_HOME" \
  XDG_DATA_HOME="$NVIM_DATA_HOME" \
  NVIM_APPNAME=nvim \
  NVIM_SOURCE_ROOT="$NVIM_SOURCE_ROOT" \
  nvim --headless -i NONE -u "$FETCH_SCRIPT" \
    -c 'lua print("NVIM_CONFIG=" .. vim.fn.stdpath("config")); print("NVIM_DATA=" .. vim.fn.stdpath("data"))' \
    -c 'qa!'; then
  NVIM_STATUS=0
else
  NVIM_STATUS=$?
fi

if (( NVIM_STATUS != 0 )); then
  echo "Neovim plugin prefetch failed with exit code $NVIM_STATUS" >&2
  exit "$NVIM_STATUS"
fi

PLUGIN_DIR="$STAGE/.data/$(nvim_data_dir_name)/site/pack/core/opt"
if [[ ! -d "$PLUGIN_DIR" ]]; then
  echo "Plugin directory is missing: $PLUGIN_DIR" >&2
  echo "Stage data contents:" >&2
  find "$STAGE/.data" -maxdepth 6 -print >&2
  exit 1
fi

PLUGIN_COUNT="$(find "$PLUGIN_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d '[:space:]')"
echo "Fetched $PLUGIN_COUNT plugin directories into $PLUGIN_DIR"
