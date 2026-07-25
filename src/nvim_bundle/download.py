from __future__ import annotations

import hashlib
import re
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class DownloadError(RuntimeError):
    """A download or integrity check failed."""


class DownloadNotFound(DownloadError):
    """The requested release asset does not exist."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_checksum(path: Path) -> str:
    fields = path.read_text(encoding="utf-8").split()
    if not fields or re.fullmatch(r"[0-9a-fA-F]{64}", fields[0]) is None:
        raise DownloadError(f"Invalid SHA-256 file: {path}")
    return fields[0].lower()


def download(url: str, destination: Path, *, retries: int = 3) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    last_error: Exception | None = None

    for attempt in range(retries):
        try:
            with tempfile.NamedTemporaryFile(
                prefix=f".{destination.name}.",
                dir=destination.parent,
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
            request = Request(url, headers={"User-Agent": "nvim-bundle/0.1"})
            with urlopen(request, timeout=60) as response, temporary.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            temporary.replace(destination)
            return
        except HTTPError as exc:
            if exc.code == 404:
                raise DownloadNotFound(f"Release asset was not found: {url}") from exc
            last_error = exc
        except (OSError, URLError) as exc:
            last_error = exc
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
                temporary = None
        if attempt + 1 < retries:
            time.sleep(2**attempt)

    raise DownloadError(f"Could not download {url}: {last_error}") from last_error


def download_checked(url: str, destination: Path, expected_sha256: str) -> None:
    download(url, destination)
    actual = sha256_file(destination)
    if actual != expected_sha256.lower():
        destination.unlink(missing_ok=True)
        raise DownloadError(
            f"SHA-256 mismatch for {destination.name}: expected {expected_sha256}, got {actual}"
        )
