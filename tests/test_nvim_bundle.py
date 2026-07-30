from __future__ import annotations

import tempfile
import unittest
import zipfile
import io
import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from nvim_bundle.blink import fetch_blink
from nvim_bundle.cli import build_parser
from nvim_bundle.download import (
    DownloadError,
    DownloadNotFound,
    download,
    download_checked,
    parse_checksum,
)
from nvim_bundle.install import _extract_archive
from nvim_bundle.models import NVIM_ASSETS, TARGETS
from nvim_bundle.package import _remove_readonly, archive_name, create_archive
from nvim_bundle.tools import load_asset_config, parse_manifest, tool_statuses
from nvim_bundle.runtime import host_key
from nvim_bundle.treesitter import find_parser_source, find_scanner_source


class TargetTests(unittest.TestCase):
    def test_all_release_targets_have_native_metadata(self) -> None:
        self.assertEqual(
            set(TARGETS),
            {
                "linux-x86_64-musl",
                "linux-aarch64-musl",
                "macos-arm64",
                "windows-x86_64",
            },
        )
        self.assertTrue(TARGETS["linux-x86_64-musl"].is_linux_musl)
        self.assertFalse(TARGETS["macos-arm64"].is_linux_musl)

    @patch("platform.system", return_value="Darwin")
    @patch("platform.machine", return_value="arm64")
    def test_host_key_normalizes_platform(self, _machine, _system) -> None:
        self.assertEqual(host_key(), ("Darwin", "arm64"))

    def test_nvim_asset_checksums_are_sha256(self) -> None:
        for asset in NVIM_ASSETS.values():
            self.assertRegex(asset.expected_sha256, r"^[0-9a-f]{64}$")

    def test_profiles_and_archive_names(self) -> None:
        target = TARGETS["macos-arm64"]
        self.assertEqual(archive_name(target, "core"), "nvim-config-macos-arm64.tar.zst")
        self.assertEqual(archive_name(target, "full"), "nvim-config-macos-arm64-full.tar.zst")
        with self.assertRaises(ValueError):
            archive_name(target, "unknown")

    def test_package_profile_defaults_to_core(self) -> None:
        args = build_parser().parse_args(["package", "--target", "macos-arm64"])
        self.assertEqual(args.profile, "core")

    def test_tool_assets_have_fixed_checksums(self) -> None:
        root = Path(__file__).parents[1]
        config = load_asset_config(root)
        self.assertEqual(config["schema_version"], 1)
        self.assertTrue(config["node_packages"])

    def test_platform_tool_statuses_are_explicit(self) -> None:
        root = Path(__file__).parents[1]
        macos = tool_statuses(root, TARGETS["macos-arm64"])
        linux_arm = tool_statuses(root, TARGETS["linux-aarch64-musl"])
        self.assertEqual(macos["prettier"], "bundled")
        self.assertEqual(linux_arm["prettier"], "external")
        self.assertEqual(linux_arm["rust-analyzer"], "unsupported")


class DownloadTests(unittest.TestCase):
    def test_parse_checksum_requires_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checksum"
            path.write_text("a" * 64 + "  file\n", encoding="utf-8")
            self.assertEqual(parse_checksum(path), "a" * 64)

            path.write_text("bad\n", encoding="utf-8")
            with self.assertRaises(DownloadError):
                parse_checksum(path)

    def test_missing_download_has_distinct_error(self) -> None:
        self.assertTrue(issubclass(DownloadNotFound, DownloadError))

    @patch("nvim_bundle.download.urlopen", side_effect=HTTPError("url", 404, "missing", {}, None))
    def test_http_404_is_not_found(self, _urlopen) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(DownloadNotFound):
                download("https://example.invalid/missing", Path(directory) / "asset")

    def test_checksum_mismatch_removes_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "asset"
            path.write_bytes(b"asset")
            with patch("nvim_bundle.download.download") as mocked:
                mocked.side_effect = lambda _url, destination: destination.write_bytes(b"asset")
                with self.assertRaises(DownloadError):
                    download_checked("https://example.invalid/asset", path, "0" * 64)
            self.assertFalse(path.exists())


class ManifestTests(unittest.TestCase):
    def test_manifest_statuses_and_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tool-manifest.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "profile": "full",
                        "target": "macos-arm64",
                        "tools": {
                            "stylua": {
                                "status": "bundled",
                                "version": "1",
                                "path": "bin/stylua",
                                "source_sha256": "a" * 64,
                            },
                            "jdtls": {"status": "external", "reason": "JDK"},
                            "hyprls": {"status": "unsupported", "reason": "platform"},
                        },
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(parse_manifest(path)["profile"], "full")

            path.write_text(path.read_text().replace('"unsupported"', '"missing"'), encoding="utf-8")
            with self.assertRaises(Exception):
                parse_manifest(path)


class ArchiveTests(unittest.TestCase):
    def test_full_archive_contains_manifest_core_does_not(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            core_root = root / "core"
            full_root = root / "full"
            for bundle_root in (core_root, full_root):
                (bundle_root / "nvim").mkdir(parents=True)
                (bundle_root / "nvim" / "init.lua").write_text("return {}", encoding="utf-8")
            (full_root / "nvim" / "tool-manifest.json").write_text("{}", encoding="utf-8")
            core_archive = root / "core.tar.zst"
            full_archive = root / "full.tar.zst"
            create_archive(core_root, core_archive)
            create_archive(full_root, full_archive)

            def names(path: Path) -> set[str]:
                data = subprocess.run(
                    ["zstd", "-d", "-c", str(path)], check=True, capture_output=True
                ).stdout
                with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as stream:
                    return set(stream.getnames())

            self.assertNotIn("nvim/tool-manifest.json", names(core_archive))
            self.assertIn("nvim/tool-manifest.json", names(full_archive))


class ResolverTests(unittest.TestCase):
    def test_bundled_resolver_fallback(self) -> None:
        nvim = shutil.which("nvim")
        if not nvim:
            self.skipTest("Neovim is not installed")
        with tempfile.TemporaryDirectory() as directory:
            config_home = Path(directory)
            bundle = config_home / "nvim"
            tool = bundle / "bin" / "test-tool"
            tool.parent.mkdir(parents=True)
            tool.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            tool.chmod(0o755)
            (bundle / "tool-manifest.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "profile": "full",
                        "target": "test",
                        "tools": {
                            "test-tool": {
                                "status": "bundled",
                                "version": "1",
                                "path": "bin/test-tool",
                            },
                            "external-tool": {"status": "external"},
                            "unsupported-tool": {"status": "unsupported"},
                        },
                    }
                ),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env.update({"XDG_CONFIG_HOME": str(config_home), "NVIM_APPNAME": "nvim", "PATH": "/usr/bin:/bin"})
            lua_root = Path(__file__).parents[1] / "lua"
            command = (
                f"package.path='{lua_root}/?.lua;'..package.path; "
                "local path,status=require('tool_resolver').resolve('test-tool'); "
                "assert(status=='bundled'); assert(path:match('test%-tool')); "
                "local external,external_status=require('tool_resolver').resolve('external-tool'); "
                "assert(external==nil and external_status=='external'); "
                "local unsupported,unsupported_status=require('tool_resolver').resolve('unsupported-tool'); "
                "assert(unsupported==nil and unsupported_status=='unsupported');"
            )
            subprocess.run(
                [nvim, "--headless", "-i", "NONE", "-u", "NONE", "+lua", command, "+qa!"],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )


class BlinkTests(unittest.TestCase):
    @patch("nvim_bundle.blink.run")
    @patch("nvim_bundle.blink.build_from_source")
    @patch("nvim_bundle.blink.download", side_effect=DownloadNotFound("missing"))
    @patch("nvim_bundle.blink.require_tools")
    def test_404_uses_source_fallback(self, _require_tools, _download, build, _run) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory) / "stage"
            fetch_blink(Path(directory), stage, TARGETS["macos-arm64"])
            version_files = list(stage.rglob("blink.cmp/target/release/version"))
            self.assertEqual(version_files, [])
        build.assert_called_once()

    @patch("nvim_bundle.blink.build_from_source")
    @patch("nvim_bundle.blink.download", side_effect=DownloadError("bad checksum"))
    @patch("nvim_bundle.blink.require_tools")
    def test_integrity_error_does_not_use_source_fallback(
        self, _require_tools, _download, build
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(DownloadError):
                fetch_blink(Path(directory), Path(directory) / "stage", TARGETS["macos-arm64"])
        build.assert_not_called()


class InstallTests(unittest.TestCase):
    def test_zip_archive_extracts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "nvim.zip"
            with zipfile.ZipFile(archive, "w") as stream:
                stream.writestr("nvim-win64/bin/nvim.exe", "binary")
            destination = root / "extracted"
            _extract_archive(archive, destination)
            self.assertEqual(
                (destination / "nvim-win64" / "bin" / "nvim.exe").read_text(),
                "binary",
            )

    @patch("nvim_bundle.package.os.chmod")
    def test_readonly_cleanup_retries(self, chmod) -> None:
        removed = []

        def remove(path):
            removed.append(path)

        _remove_readonly(remove, "locked", PermissionError("denied"))

        chmod.assert_called_once()
        self.assertEqual(removed, ["locked"])


class TreeSitterTests(unittest.TestCase):
    def test_parser_source_prefers_known_project_layout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preferred = root / "tree-sitter-markdown" / "src"
            preferred.mkdir(parents=True)
            preferred.joinpath("parser.c").touch()
            self.assertEqual(find_parser_source(root, "markdown"), preferred / "parser.c")

    def test_scanner_source_supports_c_and_cpp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.joinpath("scanner.cpp").touch()
            self.assertEqual(find_scanner_source(root), root / "scanner.cpp")


if __name__ == "__main__":
    unittest.main()
