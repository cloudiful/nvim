from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from nvim_bundle.blink import fetch_blink
from nvim_bundle.download import (
    DownloadError,
    DownloadNotFound,
    download,
    download_checked,
    parse_checksum,
)
from nvim_bundle.install import _extract_archive
from nvim_bundle.models import TARGETS
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
