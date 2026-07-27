from __future__ import annotations

import shutil
from pathlib import Path

from .download import DownloadError, DownloadNotFound, download, parse_checksum, sha256_file
from .models import DEFAULT_BLINK_RELEASE_BASE, DEFAULT_BLINK_VERSION, Target
from .runtime import BuildError, data_dir_name, environment, require_tools, run


def fetch_blink(
    root: Path,
    stage: Path,
    target: Target,
    *,
    version: str = DEFAULT_BLINK_VERSION,
    base_url: str | None = None,
) -> None:
    require_tools("nvim")
    plugin_dir = stage / ".data" / data_dir_name() / "site" / "pack" / "core" / "opt" / "blink.cmp"
    library_dir = plugin_dir / "target" / "release"
    library_dir.mkdir(parents=True, exist_ok=True)
    base_url = base_url or f"{DEFAULT_BLINK_RELEASE_BASE}/{version}"
    asset_url = f"{base_url.rstrip('/')}/{target.rust_triple}{target.blink_extension}"
    library = library_dir / target.blink_library
    checksum_file = library_dir / f"{target.blink_library}.sha256"

    try:
        download(asset_url, library)
        download(f"{asset_url}.sha256", checksum_file)
        expected = parse_checksum(checksum_file)
        actual = sha256_file(library)
        if actual != expected:
            raise DownloadError(
                f"SHA-256 mismatch for {library.name}: expected {expected}, got {actual}"
            )
    except DownloadNotFound:
        library.unlink(missing_ok=True)
        checksum_file.unlink(missing_ok=True)
        build_from_source(plugin_dir, target, library)

    patch_script = root / "scripts" / "patch_blink_offline.lua"
    env = environment(BLINK_PLUGIN_DIR=plugin_dir, BLINK_VERSION=version)
    run(["nvim", "--headless", "-i", "NONE", "-u", "NONE", "-l", patch_script], env=env)


def build_from_source(plugin_dir: Path, target: Target, output: Path) -> None:
    require_tools("rustup", "cargo")
    linker_env = {}
    if target.rust_triple == "x86_64-unknown-linux-musl":
        linker_env["CARGO_TARGET_X86_64_UNKNOWN_LINUX_MUSL_LINKER"] = "cc"
    elif target.rust_triple == "aarch64-unknown-linux-musl":
        linker_env["CARGO_TARGET_AARCH64_UNKNOWN_LINUX_MUSL_LINKER"] = "cc"
    run(["rustup", "target", "add", target.rust_triple])
    run(
        [
            "cargo",
            "build",
            "--release",
            "--target",
            target.rust_triple,
            "--manifest-path",
            plugin_dir / "Cargo.toml",
        ],
        env=environment(**linker_env),
    )
    built = plugin_dir / "target" / target.rust_triple / "release" / target.blink_library
    if not built.is_file():
        raise BuildError(f"Cargo did not produce {built}")
    shutil.copy2(built, output)
    checksum = sha256_file(output)
    output.with_name(f"{output.name}.sha256").write_text(
        f"{checksum}  {output.name}\n", encoding="utf-8"
    )
