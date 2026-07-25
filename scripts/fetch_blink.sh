#!/usr/bin/env bash
set -euo pipefail

STAGE="${NVIM_BUNDLE_STAGE:?NVIM_BUNDLE_STAGE is required}"
TARGET="${NVIM_BUNDLE_TARGET:?NVIM_BUNDLE_TARGET is required}"
VERSION="${BLINK_VERSION:-v1.10.2}"
BLINK_DIR="$STAGE/.data/nvim/site/pack/core/opt/blink.cmp"
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/nvim_paths.sh"

NVIM_BLINK_DIR="$(nvim_native_path "$BLINK_DIR")"
PATCH_SCRIPT="$(nvim_native_path "$ROOT/scripts/patch_blink_offline.lua")"
BASE_URL="${BLINK_RELEASE_BASE_URL:-https://github.com/Saghen/blink.cmp/releases/download/$VERSION}"

case "$TARGET" in
  linux-x86_64-musl)
    TRIPLE="x86_64-unknown-linux-musl"
    EXT=".so"
    LIB_NAME="libblink_cmp_fuzzy.so"
    ;;
  linux-aarch64-musl)
    TRIPLE="aarch64-unknown-linux-musl"
    EXT=".so"
    LIB_NAME="libblink_cmp_fuzzy.so"
    ;;
  macos-arm64)
    TRIPLE="aarch64-apple-darwin"
    EXT=".dylib"
    LIB_NAME="libblink_cmp_fuzzy.dylib"
    ;;
  windows-x86_64)
    TRIPLE="x86_64-pc-windows-msvc"
    EXT=".dll"
    LIB_NAME="blink_cmp_fuzzy.dll"
    ;;
  *)
    echo "Unsupported target: $TARGET" >&2
    exit 1
    ;;
esac

LIB_DIR="$BLINK_DIR/target/release"
mkdir -p "$LIB_DIR"

download_prebuilt() {
  curl --fail --location --retry 3 \
    "$BASE_URL/$TRIPLE$EXT" \
    --output "$LIB_DIR/$LIB_NAME"
  curl --fail --location --retry 3 \
    "$BASE_URL/$TRIPLE$EXT.sha256" \
    --output "$LIB_DIR/$LIB_NAME.sha256"

  EXPECTED="$(awk '{print $1}' "$LIB_DIR/$LIB_NAME.sha256")"
  if command -v sha256sum >/dev/null 2>&1; then
    ACTUAL="$(sha256sum "$LIB_DIR/$LIB_NAME" | awk '{print $1}')"
  else
    ACTUAL="$(shasum -a 256 "$LIB_DIR/$LIB_NAME" | awk '{print $1}')"
  fi
  test "$EXPECTED" = "$ACTUAL"
}

if ! download_prebuilt; then
  rm -f "$LIB_DIR/$LIB_NAME" "$LIB_DIR/$LIB_NAME.sha256"
  case "$TRIPLE" in
    x86_64-unknown-linux-musl)
      export CARGO_TARGET_X86_64_UNKNOWN_LINUX_MUSL_LINKER="${CC:-cc}"
      ;;
    aarch64-unknown-linux-musl)
      export CARGO_TARGET_AARCH64_UNKNOWN_LINUX_MUSL_LINKER="${CC:-cc}"
      ;;
  esac
  rustup target add "$TRIPLE"
  cargo build --release --target "$TRIPLE" --manifest-path "$BLINK_DIR/Cargo.toml"
  cp "$BLINK_DIR/target/$TRIPLE/release/$LIB_NAME" "$LIB_DIR/$LIB_NAME"
  if command -v sha256sum >/dev/null 2>&1; then
    CHECKSUM="$(sha256sum "$LIB_DIR/$LIB_NAME" | awk '{print $1}')"
  else
    CHECKSUM="$(shasum -a 256 "$LIB_DIR/$LIB_NAME" | awk '{print $1}')"
  fi
  printf '%s  %s\n' "$CHECKSUM" "$LIB_NAME" > "$LIB_DIR/$LIB_NAME.sha256"
fi

printf '%s\n' "$VERSION" > "$LIB_DIR/version"

BLINK_PLUGIN_DIR="$NVIM_BLINK_DIR" \
BLINK_VERSION="$VERSION" \
nvim --headless -u NONE -l "$PATCH_SCRIPT"
