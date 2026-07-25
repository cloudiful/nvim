#!/usr/bin/env bash
set -euo pipefail

STAGE="${NVIM_BUNDLE_STAGE:?NVIM_BUNDLE_STAGE is required}"
TARGET="${NVIM_BUNDLE_TARGET:?NVIM_BUNDLE_TARGET is required}"
CACHE_DIR="$STAGE/.build/cache/nvim"
INSTALL_DIR="$STAGE/runtime/parser"
LANGUAGE_FILE="${TREESITTER_LANGUAGES_FILE:?TREESITTER_LANGUAGES_FILE is required}"

case "$TARGET" in
  linux-x86_64-musl)
    ZIG_TARGET="x86_64-linux-musl"
    ;;
  linux-aarch64-musl)
    ZIG_TARGET="aarch64-linux-musl"
    ;;
  *)
    echo "Unsupported Tree-sitter cross target: $TARGET" >&2
    exit 1
    ;;
esac

CC=(zig cc -target "$ZIG_TARGET")
CXX=(zig c++ -target "$ZIG_TARGET")

while IFS= read -r language || [[ -n "$language" ]]; do
  [[ -z "$language" ]] && continue

  project_dir="$CACHE_DIR/tree-sitter-$language"
  source_hint=""
  case "$language" in
    markdown)
      source_hint="tree-sitter-markdown"
      ;;
    markdown_inline)
      source_hint="tree-sitter-markdown-inline"
      ;;
    tsx)
      source_hint="tsx"
      ;;
    typescript)
      source_hint="typescript"
      ;;
    xml)
      source_hint="xml"
      ;;
  esac

  if [[ -n "$source_hint" && -f "$project_dir/$source_hint/src/parser.c" ]]; then
    parser_source="$project_dir/$source_hint/src/parser.c"
  else
    parser_source="$(find "$project_dir" -type f -path '*/src/parser.c' -print -quit)"
  fi
  if [[ -z "$parser_source" ]]; then
    echo "Missing parser source for $language under $project_dir" >&2
    exit 1
  fi

  source_dir="$(dirname -- "$parser_source")"
  object_dir="$STAGE/.build/cross/$language"
  output="$INSTALL_DIR/$language.so"
  temp_output="$output.tmp"
  rm -rf "$object_dir"
  mkdir -p "$object_dir"

  parser_object="$object_dir/parser.o"
  "${CC[@]}" -O2 -fPIC -std=c11 -I "$source_dir" -c "$parser_source" -o "$parser_object"
  objects=("$parser_object")
  linker=("${CC[@]}")

  scanner_source="$(find "$source_dir" -maxdepth 1 -type f \( -name scanner.c -o -name scanner.cc -o -name scanner.cpp \) -print -quit)"
  if [[ -n "$scanner_source" ]]; then
    scanner_ext="${scanner_source##*.}"
    scanner_object="$object_dir/scanner.o"
    if [[ "$scanner_ext" == "c" ]]; then
      "${CC[@]}" -O2 -fPIC -std=c11 -I "$source_dir" -c "$scanner_source" -o "$scanner_object"
    else
      "${CXX[@]}" -O2 -fPIC -I "$source_dir" -c "$scanner_source" -o "$scanner_object"
      linker=("${CXX[@]}")
    fi
    objects+=("$scanner_object")
  fi

  mkdir -p "$INSTALL_DIR"
  "${linker[@]}" -shared "${objects[@]}" -o "$temp_output"
  mv -f "$temp_output" "$output"

  if command -v readelf >/dev/null 2>&1; then
    machine="$(readelf -h "$output" | awk -F: '/Machine:/ {gsub(/^[[:space:]]+/, "", $2); print $2}')"
    case "$TARGET:$machine" in
      linux-x86_64-musl:*X86-64*) ;;
      linux-aarch64-musl:*AArch64*) ;;
      *)
        echo "Unexpected parser architecture for $language: $machine" >&2
        exit 1
        ;;
    esac
  fi
  echo "Built $language for $ZIG_TARGET"
done < "$LANGUAGE_FILE"
