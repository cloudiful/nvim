from __future__ import annotations

import argparse
from pathlib import Path

from .install import install_nvim, install_tree_sitter
from .models import (
    DEFAULT_BLINK_VERSION,
    DEFAULT_TREE_SITTER_SOURCE,
    DEFAULT_NVIM_VERSION,
    DEFAULT_TREE_SITTER_VERSION,
    PROFILES,
    TARGETS,
)
from .package import PackageOptions, package_bundle
from .runtime import BuildError, fail
from .updater import CHECK_CLEAN, CHECK_DRIFT, check_pins, update_pins


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _path(value: str, root: Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else root / path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nvim-bundle",
        description="Build the portable Neovim configuration bundle.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=repository_root(),
        help=argparse.SUPPRESS,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    nvim = subparsers.add_parser("install-nvim", help="Install the host Neovim binary.")
    nvim.add_argument("--version", default=DEFAULT_NVIM_VERSION)

    tree_sitter = subparsers.add_parser(
        "install-tree-sitter", help="Install the host Tree-sitter CLI."
    )
    tree_sitter.add_argument("--version", default=DEFAULT_TREE_SITTER_VERSION)

    package = subparsers.add_parser("package", help="Build and verify a target bundle.")
    package.add_argument("--target", choices=tuple(TARGETS), required=True)
    package.add_argument("--profile", choices=PROFILES, default="core")
    package.add_argument("--output-dir", default=".build/output")
    package.add_argument("--work-dir", default=".build")
    package.add_argument("--blink-version", default=DEFAULT_BLINK_VERSION)
    package.add_argument("--blink-base-url")
    package.add_argument("--treesitter-source", default=DEFAULT_TREE_SITTER_SOURCE)
    package.add_argument("--treesitter-max-jobs", type=int)

    update_parser = subparsers.add_parser(
        "update-pins", help="Update pinned Neovim and plugin revisions."
    )
    update_parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Report drift without writing pins "
            f"(exit {CHECK_CLEAN} in sync, {CHECK_DRIFT} drift available)."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == "install-nvim":
            install_nvim(root, args.version)
        elif args.command == "install-tree-sitter":
            install_tree_sitter(args.version, root=root)
        elif args.command == "package":
            package_bundle(
                root,
                PackageOptions(
                    target=TARGETS[args.target],
                    profile=args.profile,
                    output_dir=_path(args.output_dir, root),
                    work_dir=_path(args.work_dir, root),
                    blink_version=args.blink_version,
                    blink_base_url=args.blink_base_url,
                    treesitter_source=args.treesitter_source,
                    treesitter_max_jobs=args.treesitter_max_jobs,
                ),
            )
        elif args.command == "update-pins":
            if args.check:
                in_sync, report = check_pins(root)
                print(report)
                return CHECK_CLEAN if in_sync else CHECK_DRIFT
            summary = update_pins(root)
            if not summary.nvim_changed and not summary.plugin_changes:
                print(f"pins are in sync (Neovim {summary.nvim_version})")
            else:
                if summary.nvim_changed:
                    print(f"Neovim -> {summary.nvim_version}")
                for name, (_, new_rev) in sorted(summary.plugin_changes.items()):
                    print(f"{name} -> {new_rev}")
                if summary.fallbacks:
                    print(
                        "fallbacks (default-branch, not stable): "
                        + ", ".join(summary.fallbacks)
                    )
        else:
            parser.error(f"unknown command: {args.command}")
    except BuildError as exc:
        fail(str(exc))
        return 1
    except KeyboardInterrupt:
        fail("interrupted")
        return 130
    return 0
