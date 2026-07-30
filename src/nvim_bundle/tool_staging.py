from __future__ import annotations

import gzip
import os
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from .runtime import BuildError, environment, run


def _asset(config: dict, name: str, target: Any) -> dict | None:
    entry = config["assets"].get(name)
    if not entry:
        return None
    selected = entry["targets"].get(target.name)
    if selected is None:
        return None
    return {**entry, **selected}


def _download_asset(cache: Path, asset: dict) -> Path:
    from .download import download_checked, sha256_file

    cache.mkdir(parents=True, exist_ok=True)
    filename = Path(asset["url"]).name or asset["sha256"]
    destination = cache / f'{asset["sha256"]}-{filename}'
    if not destination.is_file() or sha256_file(destination) != asset["sha256"]:
        download_checked(asset["url"], destination, asset["sha256"])
    return destination


def _extract(archive: Path, destination: Path, fmt: str) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    if fmt == "tar.gz":
        with tarfile.open(archive, "r:gz") as stream:
            stream.extractall(destination, filter="data")
    elif fmt == "tar.xz":
        with tarfile.open(archive, "r:xz") as stream:
            stream.extractall(destination, filter="data")
    elif fmt == "zip":
        with zipfile.ZipFile(archive) as stream:
            stream.extractall(destination)
    elif fmt == "gz":
        output = destination / archive.name
        with gzip.open(archive, "rb") as source, output.open("wb") as target:
            shutil.copyfileobj(source, target)
    else:
        raise BuildError(f"Unsupported tool asset format: {fmt}")
    return destination


def _find_entry(root: Path, name: str) -> Path:
    matches = sorted(path for path in root.rglob(name) if path.is_file())
    if not matches:
        matches = sorted(path for path in root.rglob(f"{name}.exe") if path.is_file())
    if len(matches) != 1:
        raise BuildError(f"Expected one {name} in tool archive, found {len(matches)}")
    return matches[0]


def _windows_path(value: str) -> str:
    return value.replace("/", "\\")


def _find_rust_runtime_library_dir(root: Path) -> Path:
    directories = sorted(
        {
            path.parent
            for path in root.rglob("*rustc_driver*")
            if path.is_file()
        }
    )
    if len(directories) != 1:
        raise BuildError(
            f"Expected one Rust runtime library directory in {root}, found {len(directories)}"
        )
    return directories[0]


def _write_wrapper(
    stage: Path,
    target: Any,
    name: str,
    runtime_path: str,
    entry: str | None,
    cwd: str | None = None,
    library_path: str | None = None,
) -> Path:
    windows = target.name.startswith("windows-")
    suffix = ".cmd" if windows else ""
    path = stage / "bin" / f"{name}{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    if windows:
        command = '@echo off\r\nset "BUNDLE=%~dp0.."\r\n'
        if library_path:
            command += f'set "PATH=%BUNDLE%\\{_windows_path(library_path)};%PATH%"\r\n'
        if cwd:
            command += f'cd /d "%BUNDLE%\\{_windows_path(cwd)}"\r\n'
        command += f'"%BUNDLE%\\{_windows_path(runtime_path)}" --'
        if entry:
            command += f' "%BUNDLE%\\{_windows_path(entry)}"'
        command += " %*\r\n"
        path.write_text(command, encoding="utf-8", newline="")
    else:
        command = "#!/bin/sh\nset -eu\nBUNDLE=$(CDPATH= cd \"$(dirname \"$0\")/..\" && pwd -P)\n"
        if library_path:
            command += f'export DYLD_LIBRARY_PATH="$BUNDLE/{library_path}${{DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}}"\n'
            command += f'export LD_LIBRARY_PATH="$BUNDLE/{library_path}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"\n'
        if cwd:
            command += f'cd "$BUNDLE/{cwd}"\n'
        command += f'exec "$BUNDLE/{runtime_path}" --'
        if entry:
            command += f' "$BUNDLE/{entry}"'
        command += ' "$@"\n'
        path.write_text(command, encoding="utf-8")
        path.chmod(path.stat().st_mode | 0o111)
    return path


def stage_node(stage: Path, target: Any, config: dict, cache: Path) -> dict[str, Path]:
    asset = _asset(config, "node", target)
    if asset is None:
        return {}
    runtime = stage / ".runtime"
    node_root = runtime / "node"
    with tempfile.TemporaryDirectory(dir=cache) as temporary:
        extracted = _extract(_download_asset(cache, asset), Path(temporary) / "node", asset["format"])
        roots = [path for path in extracted.iterdir()]
        source = roots[0] if len(roots) == 1 and roots[0].is_dir() else extracted
        shutil.copytree(source, node_root)

    windows = target.name.startswith("windows-")
    node = node_root / ("node.exe" if windows else "bin/node")
    npm = node_root / (
        "node_modules/npm/bin/npm-cli.js" if windows else "lib/node_modules/npm/bin/npm-cli.js"
    )
    if not node.is_file() or not npm.is_file():
        raise BuildError(f"Node runtime is incomplete under {node_root}")

    package_files = [_download_asset(cache, package) for package in config["node_packages"]]
    run(
        [
            node,
            npm,
            "install",
            "--prefix",
            runtime,
            "--ignore-scripts",
            "--no-audit",
            "--no-fund",
            "--no-package-lock",
            "--omit=dev",
            *package_files,
        ],
        env=environment(NPM_CONFIG_UPDATE_NOTIFIER="false"),
    )
    shutil.rmtree(runtime / "node_modules" / ".cache", ignore_errors=True)
    return {"node": node}


def stage_native(
    stage: Path,
    target: Any,
    definition: Any,
    asset: dict,
    config: dict,
    cache: Path,
) -> Path:
    archive = _download_asset(cache, asset)
    windows = target.name.startswith("windows-")
    output = stage / "bin" / (definition.name + (".exe" if windows else ""))
    output.parent.mkdir(parents=True, exist_ok=True)
    library_path = None

    if definition.runtime_asset:
        runtime_asset = _asset(config, definition.runtime_asset, target)
        if runtime_asset is None:
            raise BuildError(f"Missing runtime asset for {definition.name}: {definition.runtime_asset}")
        runtime_root = stage / ".runtime" / definition.name
        with tempfile.TemporaryDirectory(dir=cache) as temporary:
            extracted_runtime = _extract(
                _download_asset(cache, runtime_asset),
                Path(temporary) / "runtime",
                runtime_asset["format"],
            )
            library_source = _find_rust_runtime_library_dir(extracted_runtime)
            shutil.copytree(library_source, runtime_root / "lib")
        library_path = str((runtime_root / "lib").relative_to(stage)).replace(os.sep, "/")

    if asset["format"] == "raw":
        binary = archive
    else:
        with tempfile.TemporaryDirectory(dir=cache) as temporary:
            extracted = _extract(archive, Path(temporary) / "asset", asset["format"])
            if definition.preserve_runtime:
                runtime_root = stage / ".runtime" / definition.name
                roots = [path for path in extracted.iterdir()]
                source = roots[0] if len(roots) == 1 and roots[0].is_dir() else extracted
                shutil.copytree(source, runtime_root)
                binary = _find_entry(runtime_root, definition.source_name or definition.name)
                return _write_wrapper(
                    stage,
                    target,
                    definition.name,
                    str(binary.relative_to(stage)).replace(os.sep, "/"),
                    None,
                    cwd=str(runtime_root.relative_to(stage)).replace(os.sep, "/"),
                )
            binary = (
                next(path for path in extracted.iterdir() if path.is_file())
                if asset["format"] == "gz"
                else _find_entry(extracted, definition.source_name or definition.name)
            )
            if definition.runtime_asset:
                return _stage_runtime_binary(
                    stage, target, definition, binary, output, library_path
                )
            shutil.copy2(binary, output)
            _make_executable(output, windows)
            return output

    if definition.runtime_asset:
        return _stage_runtime_binary(stage, target, definition, binary, output, library_path)
    shutil.copy2(binary, output)
    _make_executable(output, windows)
    return output


def _stage_runtime_binary(
    stage: Path,
    target: Any,
    definition: Any,
    binary: Path,
    output: Path,
    library_path: str | None,
) -> Path:
    windows = target.name.startswith("windows-")
    runtime_binary = output.with_name(output.name + ".bin" + (".exe" if windows else ""))
    shutil.copy2(binary, runtime_binary)
    _make_executable(runtime_binary, windows)
    return _write_wrapper(
        stage,
        target,
        definition.name,
        str(runtime_binary.relative_to(stage)).replace(os.sep, "/"),
        None,
        library_path=library_path,
    )


def _make_executable(path: Path, windows: bool) -> None:
    if not windows:
        path.chmod(path.stat().st_mode | 0o111)


def stage_node_wrappers(stage: Path, config: dict, target: Any, definitions: tuple[Any, ...]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    node_modules = stage / ".runtime" / "node_modules"
    package_entries = {item["name"]: item for item in config["node_packages"]}
    windows = target.name.startswith("windows-")
    for definition in definitions:
        if not definition.package or not definition.entry:
            continue
        package = package_entries[definition.package]
        entry = node_modules / definition.package / definition.entry
        if not entry.is_file():
            raise BuildError(f"Missing Node package entry: {entry}")
        wrapper = _write_wrapper(
            stage,
            target,
            definition.name.replace("/", "-").replace("@", ""),
            ".runtime/node/" + ("node.exe" if windows else "bin/node"),
            ".runtime/node_modules/" + definition.package + "/" + (package["entry"] or definition.entry),
        )
        result[definition.name] = wrapper
    return result
