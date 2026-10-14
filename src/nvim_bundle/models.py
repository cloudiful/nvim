from __future__ import annotations

from dataclasses import dataclass


PROFILES = ("core", "full")


@dataclass(frozen=True)
class Target:
    name: str
    rust_triple: str
    blink_extension: str
    blink_library: str
    zig_target: str | None = None
    tool_asset_name: str | None = None

    @property
    def is_linux_musl(self) -> bool:
        return self.name.startswith("linux-") and self.name.endswith("-musl")

    @property
    def is_linux_gnu(self) -> bool:
        return self.name.startswith("linux-") and self.name.endswith("-gnu")

    @property
    def tool_target(self) -> str:
        return self.tool_asset_name or self.name


def validate_profile(value: str) -> str:
    if value not in PROFILES:
        raise ValueError(f"Unsupported bundle profile: {value}")
    return value


TARGETS = {
    "linux-x86_64-musl": Target(
        name="linux-x86_64-musl",
        rust_triple="x86_64-unknown-linux-musl",
        blink_extension=".so",
        blink_library="libblink_cmp_fuzzy.so",
        zig_target="x86_64-linux-musl",
    ),
    "linux-aarch64-musl": Target(
        name="linux-aarch64-musl",
        rust_triple="aarch64-unknown-linux-musl",
        blink_extension=".so",
        blink_library="libblink_cmp_fuzzy.so",
        zig_target="aarch64-linux-musl",
    ),
    "linux-x86_64-gnu": Target(
        name="linux-x86_64-gnu",
        rust_triple="x86_64-unknown-linux-gnu",
        blink_extension=".so",
        blink_library="libblink_cmp_fuzzy.so",
        tool_asset_name="linux-x86_64-musl",
    ),
    "linux-aarch64-gnu": Target(
        name="linux-aarch64-gnu",
        rust_triple="aarch64-unknown-linux-gnu",
        blink_extension=".so",
        blink_library="libblink_cmp_fuzzy.so",
        tool_asset_name="linux-aarch64-musl",
    ),
    "macos-arm64": Target(
        name="macos-arm64",
        rust_triple="aarch64-apple-darwin",
        blink_extension=".dylib",
        blink_library="libblink_cmp_fuzzy.dylib",
    ),
    "windows-x86_64": Target(
        name="windows-x86_64",
        rust_triple="x86_64-pc-windows-msvc",
        blink_extension=".dll",
        blink_library="blink_cmp_fuzzy.dll",
    ),
}

DEFAULT_NVIM_VERSION = "0.12.6"
DEFAULT_TREE_SITTER_VERSION = "0.26.11"
DEFAULT_BLINK_VERSION = "v1.10.2"
DEFAULT_TREE_SITTER_SOURCE = "https://github.com/nvim-treesitter/nvim-treesitter.git"
DEFAULT_BLINK_RELEASE_BASE = "https://github.com/Saghen/blink.cmp/releases/download"


@dataclass(frozen=True)
class HostAsset:
    archive: str
    expected_sha256: str
    binary: str


NVIM_ASSETS = {
    ("Linux", "x86_64"): HostAsset(
        "nvim-linux-x86_64.tar.gz",
        "474430d53e6264f6d6dd18db42d6dc9df3a1b56ca9e88a325bbf860e1a811d87",
        "nvim",
    ),
    ("Linux", "aarch64"): HostAsset(
        "nvim-linux-arm64.tar.gz",
        "8f1f64a0bdb97247034038c3823c6cbad5bdf9ecd5751b85494b71c3ee04c815",
        "nvim",
    ),
    ("Darwin", "arm64"): HostAsset(
        "nvim-macos-arm64.tar.gz",
        "1dbd148222b051ba6c307c4d17a318ed083df018a4f6a5a0ce46955ffc9ab87b",
        "nvim",
    ),
    ("Windows", "x86_64"): HostAsset(
        "nvim-win64.zip",
        "4e12b7103b601ffc8f25954b4da100f339faa73dccb69a5b135e897fa3d893ed",
        "nvim.exe",
    ),
}

TREE_SITTER_ASSETS = {
    ("Linux", "x86_64"): HostAsset(
        "tree-sitter-linux-x64.gz",
        "8dac3c89bb632eece700ea7a261ad963b251f2228c4aef3b58458ebea8dbe4eb",
        "tree-sitter",
    ),
    ("Linux", "aarch64"): HostAsset(
        "tree-sitter-linux-arm64.gz",
        "e47dd59bf2f21ad7c15771546a724464ee3c008a60fbb61c6860bd19a44b3060",
        "tree-sitter",
    ),
    ("Darwin", "arm64"): HostAsset(
        "tree-sitter-macos-arm64.gz",
        "0bb646b2a29007233bd44855f00d0b8e238084d5b442f097d841b476318c2c90",
        "tree-sitter",
    ),
    ("Windows", "x86_64"): HostAsset(
        "tree-sitter-windows-x64.gz",
        "9d836a8c405ed50cea6b3410905576de3bff2b42ca12edc1e825ec86fe918a5f",
        "tree-sitter.exe",
    ),
}
