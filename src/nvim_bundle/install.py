from __future__ import annotations

import gzip
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path

from .download import download_checked
from .models import (
    DEFAULT_NVIM_VERSION,
    DEFAULT_TREE_SITTER_VERSION,
    NVIM_ASSETS,
    TREE_SITTER_ASSETS,
)
from .runtime import BuildError, append_github_path, host_key, require_tools, run


def _extract_archive(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    if archive.name.endswith(".tar.gz"):
        with tarfile.open(archive, "r:gz") as stream:
            stream.extractall(destination, filter="data")
    elif archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as stream:
            stream.extractall(destination)
    else:
        raise BuildError(f"Unsupported archive: {archive.name}")


def _find_binary(root: Path, name: str) -> Path:
    matches = sorted(path for path in root.rglob(name) if path.is_file())
    if len(matches) != 1:
        raise BuildError(f"Expected one {name} under {root}, found {len(matches)}")
    return matches[0]


def install_nvim(root: Path, version: str = DEFAULT_NVIM_VERSION) -> Path:
    asset = NVIM_ASSETS.get(host_key())
    if asset is None:
        system, machine = host_key()
        raise BuildError(f"Unsupported Neovim host: {system}/{machine}")

    host_dir = root / ".build" / "host" / "nvim"
    host_dir.parent.mkdir(parents=True, exist_ok=True)
    base_url = f"https://github.com/neovim/neovim/releases/download/v{version}"
    with tempfile.TemporaryDirectory(dir=host_dir.parent) as temporary:
        temporary_path = Path(temporary)
        archive = temporary_path / asset.archive
        download_checked(f"{base_url}/{asset.archive}", archive, asset.expected_sha256)
        extracted = temporary_path / "extracted"
        _extract_archive(archive, extracted)
        shutil.rmtree(host_dir, ignore_errors=True)
        shutil.copytree(extracted, host_dir)

    binary = _find_binary(host_dir, asset.binary)
    binary.chmod(binary.stat().st_mode | 0o111)
    append_github_path(binary.parent)
    print(f"Installed Neovim at {binary}")
    result = run([binary, "--version"], capture_output=True)
    print("\n".join(result.stdout.splitlines()[:3]))
    return binary


def install_tree_sitter(version: str = DEFAULT_TREE_SITTER_VERSION, *, root: Path) -> Path:
    asset = TREE_SITTER_ASSETS.get(host_key())
    if asset is None:
        system, machine = host_key()
        raise BuildError(f"Unsupported Tree-sitter CLI host: {system}/{machine}")

    tools_dir = root / ".build" / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    base_url = f"https://github.com/tree-sitter/tree-sitter/releases/download/v{version}"
    binary = tools_dir / asset.binary
    with tempfile.TemporaryDirectory(dir=tools_dir) as temporary:
        temporary_path = Path(temporary)
        archive = temporary_path / asset.archive
        download_checked(f"{base_url}/{asset.archive}", archive, asset.expected_sha256)
        if archive.name.endswith(".gz"):
            with gzip.open(archive, "rb") as source, binary.open("wb") as destination:
                shutil.copyfileobj(source, destination)
        else:
            raise BuildError(f"Unsupported Tree-sitter archive: {archive.name}")

    binary.chmod(binary.stat().st_mode | 0o111)
    append_github_path(tools_dir)
    print(f"Installed Tree-sitter CLI at {binary}")
    require_tools(str(binary))
    run([binary, "--version"])
    return binary
