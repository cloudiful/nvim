#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${NVIM_VERSION:-0.12.4}"
HOST_DIR="$ROOT/.build/host/nvim"
BASE_URL="https://github.com/neovim/neovim/releases/download/v$VERSION"

OS="${RUNNER_OS:-$(uname -s)}"
ARCH="${RUNNER_ARCH:-$(uname -m)}"

case "$OS:$ARCH" in
  Linux:X64|Linux:x86_64|Linux:amd64)
    ASSET="nvim-linux-x86_64.tar.gz"
    EXPECTED="012bf3fcac5ade43914df3f174668bf64d05e049a4f032a388c027b1ebd78628"
    ;;
  Linux:ARM64|Linux:aarch64|Linux:arm64)
    ASSET="nvim-linux-arm64.tar.gz"
    EXPECTED="ceb7e88c6b681f0515d135dcdfad54f5eb4373b25ce6172197cd9a69c758063f"
    ;;
  macOS:ARM64|Darwin:arm64|Darwin:ARM64)
    ASSET="nvim-macos-arm64.tar.gz"
    EXPECTED="51ab83afa66d663627c2ab1be43209b0f4e81360d4598b53efaa4d8195f24c89"
    ;;
  Windows:X64|MINGW*:x86_64|MSYS*:x86_64)
    ASSET="nvim-win64.zip"
    EXPECTED="9fc3572829ffd13debb6e32555da2c8cc02555568260a9fc4cf1f65bbcca319c"
    ;;
  *)
    echo "Unsupported Neovim host: $OS/$ARCH" >&2
    exit 1
    ;;
esac

mkdir -p "$HOST_DIR"
ARCHIVE="$HOST_DIR/$ASSET"
curl --fail --location --retry 3 --proto '=https' --tlsv1.2 \
  "$BASE_URL/$ASSET" --output "$ARCHIVE"

if command -v sha256sum >/dev/null 2>&1; then
  ACTUAL="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
else
  ACTUAL="$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')"
fi
test "$EXPECTED" = "$ACTUAL"

tar -xf "$ARCHIVE" -C "$HOST_DIR"
rm -f "$ARCHIVE"

NVIM_BIN="$(find "$HOST_DIR" -type f \( -name nvim -o -name nvim.exe \) -print -quit)"
if [[ -z "$NVIM_BIN" ]]; then
  echo "Neovim executable was not found in $ASSET" >&2
  exit 1
fi

chmod +x "$NVIM_BIN"
if [[ -n "${GITHUB_PATH:-}" ]]; then
  printf '%s\n' "$(dirname -- "$NVIM_BIN")" >> "$GITHUB_PATH"
fi

"$NVIM_BIN" --version | sed -n '1,3p'
