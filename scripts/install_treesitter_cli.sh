#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${TREE_SITTER_CLI_VERSION:-0.26.11}"
TOOLS_DIR="$ROOT/.build/tools"
BASE_URL="https://github.com/tree-sitter/tree-sitter/releases/download/v$VERSION"

# RUNNER_ARCH describes the build host. It is intentionally independent from
# the musl parser target used later by the package build.
OS="${RUNNER_OS:-$(uname -s)}"
ARCH="${RUNNER_ARCH:-$(uname -m)}"

case "$OS:$ARCH" in
  Linux:X64|Linux:x86_64|Linux:amd64)
    ASSET="tree-sitter-linux-x64.gz"
    EXPECTED="8dac3c89bb632eece700ea7a261ad963b251f2228c4aef3b58458ebea8dbe4eb"
    BINARY="tree-sitter"
    ;;
  Linux:ARM64|Linux:aarch64|Linux:arm64)
    ASSET="tree-sitter-linux-arm64.gz"
    EXPECTED="e47dd59bf2f21ad7c15771546a724464ee3c008a60fbb61c6860bd19a44b3060"
    BINARY="tree-sitter"
    ;;
  macOS:ARM64|Darwin:arm64|Darwin:ARM64)
    ASSET="tree-sitter-macos-arm64.gz"
    EXPECTED="0bb646b2a29007233bd44855f00d0b8e238084d5b442f097d841b476318c2c90"
    BINARY="tree-sitter"
    ;;
  Windows:X64|MINGW*:x86_64|MSYS*:x86_64)
    ASSET="tree-sitter-windows-x64.gz"
    EXPECTED="9d836a8c405ed50cea6b3410905576de3bff2b42ca12edc1e825ec86fe918a5f"
    BINARY="tree-sitter.exe"
    ;;
  *)
    echo "Unsupported Tree-sitter CLI host: $OS/$ARCH" >&2
    exit 1
    ;;
esac

mkdir -p "$TOOLS_DIR"
ARCHIVE="$TOOLS_DIR/$ASSET"
curl --fail --location --retry 3 --proto '=https' --tlsv1.2 \
  "$BASE_URL/$ASSET" --output "$ARCHIVE"

if command -v sha256sum >/dev/null 2>&1; then
  ACTUAL="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
else
  ACTUAL="$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')"
fi
test "$EXPECTED" = "$ACTUAL"

gzip -dc "$ARCHIVE" > "$TOOLS_DIR/$BINARY"
rm -f "$ARCHIVE"
chmod +x "$TOOLS_DIR/$BINARY"

if [[ -n "${GITHUB_PATH:-}" ]]; then
  printf '%s\n' "$TOOLS_DIR" >> "$GITHUB_PATH"
fi

"$TOOLS_DIR/$BINARY" --version
