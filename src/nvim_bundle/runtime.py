from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path


class BuildError(RuntimeError):
    """A user-actionable build failure."""


def command_text(command: Sequence[str | os.PathLike[str]]) -> str:
    return shlex.join([os.fspath(part) for part in command])


def require_tools(*names: str) -> None:
    missing = [name for name in names if shutil.which(name) is None]
    if missing:
        raise BuildError(f"Required tools are missing: {', '.join(missing)}")


def run(
    command: Sequence[str | os.PathLike[str]],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    printable = [os.fspath(part) for part in command]
    print(f"+ {command_text(printable)}", flush=True)
    try:
        return subprocess.run(
            printable,
            cwd=cwd,
            env=dict(env) if env is not None else None,
            check=True,
            text=True,
            capture_output=capture_output,
        )
    except FileNotFoundError as exc:
        raise BuildError(f"Required command was not found: {printable[0]}") from exc
    except subprocess.CalledProcessError as exc:
        suffix = f" (exit code {exc.returncode})"
        raise BuildError(f"Command failed{suffix}: {command_text(printable)}") from exc


def environment(**updates: str | Path | None) -> dict[str, str]:
    result = os.environ.copy()
    for key, value in updates.items():
        if value is not None:
            result[key] = os.fspath(value)
    return result


def append_github_path(path: Path) -> None:
    github_path = os.environ.get("GITHUB_PATH")
    if github_path:
        with open(github_path, "a", encoding="utf-8") as stream:
            stream.write(f"{path}\n")


def host_key() -> tuple[str, str]:
    import platform

    system = platform.system()
    machine = platform.machine().lower()
    system = {"Darwin": "Darwin", "Windows": "Windows", "Linux": "Linux"}.get(system, system)
    machine = {
        "amd64": "x86_64",
        "x64": "x86_64",
        "x86-64": "x86_64",
        "aarch64": "aarch64",
        "arm64": "arm64",
    }.get(machine, machine)
    return system, machine


def data_dir_name() -> str:
    return "nvim-data" if os.name == "nt" else "nvim"


def vim_file_argument(path: Path) -> str:
    """Format a path for Neovim's `:luafile` command."""
    return str(path).replace("\\", "/").replace(" ", r"\ ").replace("|", r"\|")


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
