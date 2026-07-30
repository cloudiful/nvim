from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .blink import fetch_blink
from .models import (
    DEFAULT_BLINK_VERSION,
    DEFAULT_TREE_SITTER_SOURCE,
    Target,
)
from .models import validate_profile
from .tools import stage_full_tools
from .runtime import (
    BuildError,
    data_dir_name,
    environment,
    require_tools,
    run,
    vim_file_argument,
)
from .treesitter import build_treesitter


@dataclass(frozen=True)
class PackageOptions:
    target: Target
    profile: str
    output_dir: Path
    work_dir: Path
    blink_version: str
    blink_base_url: str | None
    treesitter_source: str
    treesitter_max_jobs: int | None


def archive_name(target: Target, profile: str) -> str:
    profile = validate_profile(profile)
    suffix = "-full" if profile == "full" else ""
    return f"nvim-config-{target.name}{suffix}.tar.zst"


def package_bundle(root: Path, options: PackageOptions) -> Path:
    target = options.target
    profile = validate_profile(options.profile)
    require_tools("nvim", "git", "cargo", "rustup", "tar", "zstd")
    if target.is_linux_musl:
        require_tools("zig")

    bundle_root = options.work_dir / "bundle"
    stage = bundle_root / "nvim"
    output_dir = options.output_dir
    archive = output_dir / archive_name(target, profile)
    shutil.rmtree(bundle_root, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    archive.unlink(missing_ok=True)
    stage.mkdir(parents=True, exist_ok=True)

    for name in ("init.lua", "nvim-pack-lock.json", "README.md"):
        shutil.copy2(root / name, stage / name)
    shutil.copytree(root / "lua", stage / "lua")

    fetch_plugins(root, stage)
    build_treesitter(
        root,
        stage,
        target,
        source=options.treesitter_source,
        max_jobs=options.treesitter_max_jobs,
    )
    fetch_blink(
        root,
        stage,
        target,
        version=options.blink_version,
        base_url=options.blink_base_url,
    )

    if profile == "full":
        stage_full_tools(root, stage, target)

    plugin_root = stage / ".data" / data_dir_name() / "site" / "pack" / "core" / "opt"
    remove_git_directories(plugin_root)
    shutil.rmtree(stage / ".build", ignore_errors=True)
    verify_bundle(root, bundle_root, stage, target)
    create_archive(bundle_root, archive)
    print(archive)
    return archive


def fetch_plugins(root: Path, stage: Path) -> None:
    config_home = stage / ".build" / "config"
    data_home = stage / ".data"
    (config_home / "nvim").mkdir(parents=True, exist_ok=True)
    (data_home).mkdir(parents=True, exist_ok=True)
    env = environment(
        XDG_CONFIG_HOME=config_home,
        XDG_DATA_HOME=data_home,
        NVIM_APPNAME="nvim",
        NVIM_SOURCE_ROOT=root,
    )
    fetch_script = root / "scripts" / "fetch_plugins.lua"
    run(
        [
            "nvim",
            "--headless",
            "-i",
            "NONE",
            "-u",
            fetch_script,
            "-c",
            'lua print("NVIM_CONFIG=" .. vim.fn.stdpath("config")); print("NVIM_DATA=" .. vim.fn.stdpath("data"))',
            "-c",
            "qa!",
        ],
        env=env,
    )
    plugin_dir = data_home / data_dir_name() / "site" / "pack" / "core" / "opt"
    if not plugin_dir.is_dir():
        contents = "\n".join(str(path) for path in data_home.rglob("*"))
        raise BuildError(f"Plugin directory is missing: {plugin_dir}\nStage data contents:\n{contents}")
    count = sum(1 for path in plugin_dir.iterdir() if path.is_dir())
    lock = json.loads((root / "nvim-pack-lock.json").read_text(encoding="utf-8"))
    expected = len(lock.get("plugins", {}))
    if count != expected:
        raise BuildError(
            f"Fetched {count} plugin directories, expected {expected}: {plugin_dir}"
        )
    print(f"Fetched {count} plugin directories into {plugin_dir}")


def remove_git_directories(root: Path) -> None:
    if not root.is_dir():
        raise BuildError(f"Plugin directory is missing: {root}")
    for directory in sorted(root.rglob(".git"), reverse=True):
        if directory.is_dir():
            shutil.rmtree(directory, onexc=_remove_readonly)


def _remove_readonly(function, path, exc) -> None:
    if not isinstance(exc, PermissionError):
        raise exc
    os.chmod(path, stat.S_IWRITE)
    function(path)


def verify_bundle(root: Path, bundle_root: Path, stage: Path, target: Target) -> None:
    skip_load = "1" if target.is_linux_musl else "0"
    verify_script = root / "scripts" / "verify_bundle.lua"
    nvim = shutil.which("nvim") or "nvim"
    command = [
        nvim,
        "--headless",
        "-i",
        "NONE",
        "-u",
        stage / "init.lua",
        "-c",
        f"luafile {vim_file_argument(verify_script)}",
        "-c",
        "qa!",
    ]
    path_entries = [str(stage / "bin"), str(Path(nvim).parent)]
    env = environment(
        XDG_CONFIG_HOME=bundle_root,
        NVIM_APPNAME="nvim",
        TREESITTER_LANGUAGES_FILE=root / "build" / "treesitter-languages.txt",
        TREESITTER_SKIP_LOAD=skip_load,
        BUNDLE_PROFILE="full" if (stage / "tool-manifest.json").is_file() else "core",
        PATH=os.pathsep.join(path_entries),
    )
    run(command, env=env)


def create_archive(bundle_root: Path, archive: Path) -> None:
    try:
        tar = subprocess.Popen(
            ["tar", "-C", bundle_root, "-cf", "-", "nvim"],
            stdout=subprocess.PIPE,
        )
    except OSError as exc:
        raise BuildError(f"Could not start tar: {exc}") from exc
    assert tar.stdout is not None
    try:
        zstd = subprocess.Popen(
            ["zstd", "-T0", "-19", "-o", archive],
            stdin=tar.stdout,
        )
    except OSError as exc:
        tar.kill()
        tar.wait()
        raise BuildError(f"Could not start zstd: {exc}") from exc
    tar.stdout.close()
    zstd_returncode = zstd.wait()
    tar_returncode = tar.wait()
    if zstd_returncode != 0 or tar_returncode != 0:
        archive.unlink(missing_ok=True)
        raise BuildError(
            f"Archive creation failed (tar={tar_returncode}, zstd={zstd_returncode})"
        )
