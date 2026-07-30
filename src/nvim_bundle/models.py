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

    @property
    def is_linux_musl(self) -> bool:
        return self.name.startswith("linux-") and self.name.endswith("-musl")


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

DEFAULT_NVIM_VERSION = "0.12.4"
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
        "012bf3fcac5ade43914df3f174668bf64d05e049a4f032a388c027b1ebd78628",
        "nvim",
    ),
    ("Linux", "aarch64"): HostAsset(
        "nvim-linux-arm64.tar.gz",
        "ceb7e88c6b681f0515d135dcdfad54f5eb4373b25ce6172197cd9a69c758063f",
        "nvim",
    ),
    ("Darwin", "arm64"): HostAsset(
        "nvim-macos-arm64.tar.gz",
        "51ab83afa66d663627c2ab1be43209b0f4e81360d4598b53efaa4d8195f24c89",
        "nvim",
    ),
    ("Windows", "x86_64"): HostAsset(
        "nvim-win64.zip",
        "9fc3572829ffd13debb6e32555da2c8cc02555568260a9fc4cf1f65bbcca319c",
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
