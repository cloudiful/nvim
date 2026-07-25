#!/usr/bin/env bash

nvim_native_path() {
  local path="$1"
  local os="${RUNNER_OS:-$(uname -s)}"

  case "$os" in
    Windows|MINGW*|MSYS*)
      if ! command -v cygpath >/dev/null 2>&1; then
        echo "cygpath is required when invoking Neovim on Windows" >&2
        return 1
      fi
      cygpath -m "$path"
      ;;
    *)
      printf '%s\n' "$path"
      ;;
  esac
}
