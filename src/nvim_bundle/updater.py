"""Stable pin updater for Neovim and plugins (stdlib only).

Resolves the newest non-prerelease Neovim release (with official sha256
digests) and permitted plugin stable SemVer tags, falling back to the
default-branch commit only when a plugin has no stable tags. All proposals
are gathered and validated before any pin file is written (fail closed).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .runtime import BuildError


class PinUpdateError(BuildError):
    """A pin update or check failed before any pin write."""


NVIM_REPO = "neovim/neovim"
GITHUB_API = "https://api.github.com"

# Archive names consumed from the Neovim release; keys match models.NVIM_ASSETS.
NVIM_REQUIRED_ASSETS = (
    "nvim-linux-x86_64.tar.gz",
    "nvim-linux-arm64.tar.gz",
    "nvim-macos-arm64.tar.gz",
    "nvim-win64.zip",
)

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA64 = re.compile(r"^[0-9a-f]{64}$")
_STABLE_TAG = re.compile(r"^v?(\d+)\.(\d+)(?:\.(\d+))?$")
_GITHUB_REPO = re.compile(r"^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$")

# Exit codes for `update-pins --check` (documented in --help and CONTRIBUTING).
CHECK_CLEAN = 0
CHECK_DRIFT = 2


def _token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or None


def _headers(token: str | None) -> dict[str, str]:
    headers = {
        "User-Agent": "nvim-bundle/0.1",
        "Accept": "application/vnd.github+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _api_get_json(url: str, token: str | None) -> tuple[object, str | None]:
    """GET a GitHub API URL. Returns (payload, Link header or None)."""
    request = Request(url, headers=_headers(token))
    try:
        with urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
            link = response.headers.get("Link")
    except HTTPError as exc:
        if exc.code == 401:
            raise PinUpdateError("GitHub API authentication failed (check GITHUB_TOKEN)") from exc
        if exc.code == 403:
            raise PinUpdateError(f"GitHub API forbidden/rate-limited for {url}") from exc
        if exc.code == 404:
            raise PinUpdateError(f"GitHub API object not found: {url}") from exc
        raise PinUpdateError(f"GitHub API request failed for {url}: {exc}") from exc
    except (OSError, URLError) as exc:
        raise PinUpdateError(f"Network error fetching {url}: {exc}") from exc
    try:
        return json.loads(raw), link
    except json.JSONDecodeError as exc:
        raise PinUpdateError(f"Malformed GitHub API response for {url}") from exc


def _next_link(link: str | None) -> str | None:
    if not link:
        return None
    for part in link.split(","):
        segments = part.split(";")
        if len(segments) != 2:
            continue
        target = segments[0].strip().strip("<>")
        rel = segments[1].strip()
        if rel == 'rel="next"':
            return target
    return None


def parse_stable_semver(tag: str) -> tuple[int, int, int] | None:
    """Parse a stable SemVer tag to (major, minor, patch), else None.

    Rejects prerelease tags (any hyphen suffix) and non-numeric tags.
    Accepts an optional leading ``v`` and two or three numeric components;
    a missing patch defaults to 0. Numeric comparison must be used, never
    lexical ordering.
    """
    if "-" in tag:
        return None
    candidate = tag.strip()
    # Strip build metadata (e.g. +build) without accepting it as stable.
    if "+" in candidate:
        return None
    match = _STABLE_TAG.match(candidate)
    if match is None:
        return None
    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3)) if match.group(3) is not None else 0
    return (major, minor, patch)


def select_highest_stable_tag(tags: list[str]) -> str | None:
    """Select the highest stable SemVer tag using numeric ordering."""
    best: str | None = None
    best_version: tuple[int, int, int] | None = None
    for tag in tags:
        version = parse_stable_semver(tag)
        if version is None:
            continue
        if best_version is None or version > best_version:
            best_version = version
            best = tag
    return best


def parse_lsremote_tags(output: str) -> dict[str, str]:
    """Parse ``git ls-remote --tags`` output to tag -> commit.

    Annotated tags resolve to their peeled commit (``^{}`` lines win over
    the tag-object line). Lightweight tags use their single line.
    """
    peeled: dict[str, str] = {}
    fallback: dict[str, str] = {}
    for line in output.splitlines():
        line = line.strip()
        if not line or "\t" not in line:
            continue
        sha, ref = line.split("\t", 1)
        if not ref.startswith("refs/tags/"):
            continue
        if ref.endswith("^{}"):
            tag = ref[len("refs/tags/") : -len("^{}")]
            peeled[tag] = sha
        else:
            tag = ref[len("refs/tags/") :]
            # Skip the pseudo-ref some servers emit; real tags handled above.
            if tag.endswith("^{}"):
                continue
            fallback.setdefault(tag, sha)
    result = dict(fallback)
    result.update(peeled)
    return result


def _validate_sha40(value: str, context: str) -> str:
    normalized = value.strip().lower()
    if _SHA40.match(normalized) is None:
        raise PinUpdateError(f"Invalid commit SHA for {context}: {value!r}")
    return normalized


def _parse_digest_field(digest: object, context: str) -> str:
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        raise PinUpdateError(f"Missing or malformed sha256 digest for {context}")
    hexpart = digest[len("sha256:") :].strip().lower()
    if _SHA64.match(hexpart) is None:
        raise PinUpdateError(f"Malformed sha256 digest for {context}")
    return hexpart


def _github_repo_of(src: str) -> tuple[str, str]:
    match = _GITHUB_REPO.match(src.strip())
    if match is None:
        raise PinUpdateError(f"Unrecognized plugin source (expected GitHub): {src!r}")
    return match.group(1), match.group(2)


def _run_lsremote(args: list[str]) -> str:
    try:
        completed = subprocess.run(
            args, check=True, capture_output=True, text=True, timeout=120
        )
    except FileNotFoundError as exc:
        raise PinUpdateError("Required command was not found: git") from exc
    except subprocess.CalledProcessError as exc:
        raise PinUpdateError(f"Command failed (exit {exc.returncode}): {' '.join(args)}") from exc
    except subprocess.TimeoutExpired as exc:
        raise PinUpdateError(f"Timed out running: {' '.join(args)}") from exc
    return completed.stdout


@dataclass(frozen=True)
class NvimProposal:
    version: str
    digests: dict[str, str]


def fetch_neovim_proposal(
    token: str | None = None,
    *,
    api_get=_api_get_json,
) -> NvimProposal:
    """Resolve the newest non-prerelease Neovim version and four digests."""
    url: str | None = f"{GITHUB_API}/repos/{NVIM_REPO}/releases?per_page=100"
    releases: list[dict] = []
    guard = 0
    while url is not None:
        guard += 1
        if guard > 20:
            raise PinUpdateError("GitHub release pagination did not terminate")
        payload, link = api_get(url, token)
        if not isinstance(payload, list):
            raise PinUpdateError("Malformed GitHub releases response")
        for item in payload:
            if isinstance(item, dict):
                releases.append(item)
        url = _next_link(link)

    best_tag: str | None = None
    best_version: tuple[int, int, int] | None = None
    best_release: dict | None = None
    for release in releases:
        if release.get("draft"):
            continue
        if release.get("prerelease"):
            continue
        tag = release.get("tag_name")
        if not isinstance(tag, str):
            continue
        version = parse_stable_semver(tag)
        if version is None:
            continue
        if best_version is None or version > best_version:
            best_version = version
            best_tag = tag
            best_release = release
    if best_tag is None or best_release is None:
        raise PinUpdateError("No stable Neovim release found")
    assets = best_release.get("assets")
    if not isinstance(assets, list):
        raise PinUpdateError(f"Malformed assets for Neovim {best_tag}")
    by_name: dict[str, dict] = {}
    for asset in assets:
        if isinstance(asset, dict) and isinstance(asset.get("name"), str):
            by_name[asset["name"]] = asset
    digests: dict[str, str] = {}
    for name in NVIM_REQUIRED_ASSETS:
        asset = by_name.get(name)
        if asset is None:
            raise PinUpdateError(f"Missing Neovim asset {name} in {best_tag}")
        digests[name] = _parse_digest_field(asset.get("digest"), f"Neovim {best_tag}/{name}")
    version = best_tag[1:] if best_tag.startswith("v") else best_tag
    return NvimProposal(version=version, digests=digests)


@dataclass(frozen=True)
class PluginProposal:
    name: str
    rev: str
    tag: str | None
    fallback: bool


def _range_bounds(range_text: str) -> tuple[tuple[int, int, int], tuple[int, int, int]] | None:
    """Parse a ``1.0.0 - 2.0.0`` range to (lower, upper) inclusive-lower/exclusive-upper."""
    parts = [p.strip() for p in range_text.split("-")]
    if len(parts) != 2:
        return None
    lower = _dotted_version(parts[0])
    upper = _dotted_version(parts[1])
    if lower is None or upper is None:
        return None
    return (lower, upper)


def _dotted_version(text: str) -> tuple[int, int, int] | None:
    cleaned = text.strip().lstrip("vV")
    match = re.fullmatch(r"(\d+)\.(\d+)(?:\.(\d+))?", cleaned)
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3) or 0))


def _tag_in_range(tag: str, range_text: str | None) -> bool:
    if range_text is None:
        return True
    bounds = _range_bounds(range_text)
    if bounds is None:
        raise PinUpdateError(f"Unrecognized compatibility range: {range_text!r}")
    version = parse_stable_semver(tag)
    if version is None:
        return False
    lower, upper = bounds
    return lower <= version < upper


def resolve_plugin_pin(
    name: str,
    src: str,
    range_text: str | None,
    *,
    lsremote=_run_lsremote,
) -> PluginProposal:
    """Resolve one plugin to a stable tag commit or default-branch fallback."""
    _github_repo_of(src)
    tags_output = lsremote(["git", "ls-remote", "--tags", src])
    tag_map = parse_lsremote_tags(tags_output)
    candidates = [tag for tag in tag_map if _tag_in_range(tag, range_text)]
    selected = select_highest_stable_tag(candidates)
    if selected is not None:
        rev = _validate_sha40(tag_map[selected], f"{name} tag {selected}")
        return PluginProposal(name=name, rev=rev, tag=selected, fallback=False)
    # Development fallback: default-branch HEAD commit, explicitly not stable.
    head_output = lsremote(["git", "ls-remote", src, "HEAD"])
    head_sha: str | None = None
    for line in head_output.splitlines():
        line = line.strip()
        if not line or "\t" not in line:
            continue
        sha, ref = line.split("\t", 1)
        if ref.strip() == "HEAD":
            head_sha = sha.strip()
            break
    if head_sha is None:
        raise PinUpdateError(f"Could not resolve default-branch HEAD for {name}")
    rev = _validate_sha40(head_sha, f"{name} HEAD")
    return PluginProposal(name=name, rev=rev, tag=None, fallback=True)


def load_lock(root: Path) -> dict:
    path = root / "nvim-pack-lock.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PinUpdateError("Missing nvim-pack-lock.json") from exc
    except json.JSONDecodeError as exc:
        raise PinUpdateError("Malformed nvim-pack-lock.json") from exc


def render_lock(lock: dict) -> str:
    return json.dumps(lock, indent=2, sort_keys=True) + "\n"


def read_models_text(root: Path) -> str:
    path = root / "src" / "nvim_bundle" / "models.py"
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PinUpdateError("Missing src/nvim_bundle/models.py") from exc


def render_models(text: str, version: str, digests: dict[str, str]) -> str:
    """Replace the Neovim version constant and four asset checksums precisely."""
    updated, count = re.subn(
        r'^DEFAULT_NVIM_VERSION = "[^"]*"$',
        f'DEFAULT_NVIM_VERSION = "{version}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count == 0:
        raise PinUpdateError("Could not locate DEFAULT_NVIM_VERSION in models.py")
    # Archive -> digest replacement preserves field order and unrelated assets.
    archive_to_digest = dict(digests)
    lines = updated.splitlines(keepends=True)
    out: list[str] = []
    index = 0
    replaced: set[str] = set()
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        quoted: str | None = None
        if stripped.startswith('"') and stripped.endswith('",'):
            quoted = stripped[1:-2]
        elif stripped.startswith('"') and stripped.endswith('"'):
            quoted = stripped[1:-1]
        if quoted in archive_to_digest and index + 1 < len(lines):
            out.append(line)
            digest_line = lines[index + 1]
            if re.search(r"[0-9a-fA-F]{64}", digest_line) is None:
                raise PinUpdateError(f"Could not locate checksum after {quoted}")
            replacement, digest_count = re.subn(
                r"[0-9a-fA-F]{64}", archive_to_digest[quoted], digest_line, count=1
            )
            if digest_count == 0:
                raise PinUpdateError(f"Could not replace checksum for {quoted}")
            out.append(replacement)
            replaced.add(quoted)
            index += 2
            continue
        out.append(line)
        index += 1
    missing = set(archive_to_digest) - replaced
    if missing:
        raise PinUpdateError(f"Could not locate Neovim assets in models.py: {sorted(missing)}")
    return "".join(out)


@dataclass(frozen=True)
class PinSummary:
    nvim_version: str
    nvim_changed: bool
    plugin_changes: dict[str, tuple[str, str]]
    blink_version: str | None
    blink_changed: bool
    fallbacks: tuple[str, ...]


def gather_proposals(
    root: Path,
    *,
    token: str | None = None,
    api_get=_api_get_json,
    lsremote=_run_lsremote,
) -> tuple[NvimProposal, dict[str, PluginProposal], str | None]:
    """Gather and validate every proposal before any pin write."""
    lock = load_lock(root)
    plugins = lock.get("plugins")
    if not isinstance(plugins, dict) or not plugins:
        raise PinUpdateError("nvim-pack-lock.json has no plugins")
    nvim = fetch_neovim_proposal(token, api_get=api_get)
    proposals: dict[str, PluginProposal] = {}
    for name in sorted(plugins):
        entry = plugins[name]
        if not isinstance(entry, dict):
            raise PinUpdateError(f"Malformed lock entry for {name}")
        src = entry.get("src")
        if not isinstance(src, str) or not src:
            raise PinUpdateError(f"Missing source for {name}")
        # Preserve the existing source value exactly; resolution uses a copy.
        range_text = entry.get("version")
        if range_text is not None and not isinstance(range_text, str):
            raise PinUpdateError(f"Unrecognized compatibility range for {name}")
        proposal = resolve_plugin_pin(name, src, range_text, lsremote=lsremote)
        proposals[name] = proposal
    blink_entry = plugins.get("blink.cmp")
    blink_tag: str | None = None
    if isinstance(blink_entry, dict):
        blink_proposal = proposals.get("blink.cmp")
        if blink_proposal is None:
            raise PinUpdateError("Missing blink.cmp proposal")
        if blink_proposal.fallback or blink_proposal.tag is None:
            raise PinUpdateError("No stable 1.x blink.cmp release available")
        blink_tag = blink_proposal.tag
    return nvim, proposals, blink_tag


def _lock_with_proposals(lock: dict, proposals: dict[str, PluginProposal]) -> dict:
    updated: dict = {"plugins": {}}
    for name in sorted(lock["plugins"]):
        entry = dict(lock["plugins"][name])
        proposal = proposals[name]
        entry["rev"] = proposal.rev
        updated["plugins"][name] = entry
    # Preserve any top-level lock keys beyond "plugins" deterministically.
    for key in sorted(lock):
        if key != "plugins":
            updated[key] = lock[key]
    # Reorder so "plugins" stays first for the established file layout.
    ordered: dict = {}
    if "plugins" in updated:
        ordered["plugins"] = updated.pop("plugins")
    ordered.update(updated)
    return ordered


def update_pins(
    root: Path,
    *,
    token: str | None = None,
    api_get=_api_get_json,
    lsremote=_run_lsremote,
) -> PinSummary:
    """Resolve, validate, then write deterministic pin files."""
    token = token if token is not None else _token()
    nvim, proposals, blink_tag = gather_proposals(root, token=token, api_get=api_get, lsremote=lsremote)
    lock = load_lock(root)
    models_text = read_models_text(root)
    new_models = render_models(models_text, nvim.version, nvim.digests)

    # Blink native version must move together with the blink plugin rev.
    from .models import DEFAULT_BLINK_VERSION as current_blink

    blink_changed = blink_tag is not None and current_blink != blink_tag
    if blink_changed and blink_tag is not None:
        new_models = re.sub(
            r'^DEFAULT_BLINK_VERSION = "[^"]*"$',
            f'DEFAULT_BLINK_VERSION = "{blink_tag}"',
            new_models,
            count=1,
            flags=re.MULTILINE,
        )
        if f'DEFAULT_BLINK_VERSION = "{blink_tag}"' not in new_models:
            raise PinUpdateError("Could not update DEFAULT_BLINK_VERSION in models.py")

    new_lock = _lock_with_proposals(lock, proposals)
    new_lock_text = render_lock(new_lock)
    old_lock_text = (root / "nvim-pack-lock.json").read_text(encoding="utf-8")

    plugin_changes: dict[str, tuple[str, str]] = {}
    for name, proposal in proposals.items():
        old_rev = str(lock["plugins"][name].get("rev", ""))
        if old_rev.lower() != proposal.rev.lower():
            plugin_changes[name] = (old_rev, proposal.rev)
    nvim_changed = new_models != models_text
    lock_changed = new_lock_text != old_lock_text
    if not nvim_changed and not lock_changed:
        # Still validate the rendered files parse before reporting idempotency.
        json.loads(new_lock_text)
        compile(new_models, "models.py", "exec")
        return PinSummary(
            nvim_version=nvim.version,
            nvim_changed=False,
            plugin_changes={},
            blink_version=blink_tag,
            blink_changed=False,
            fallbacks=tuple(sorted(n for n, p in proposals.items() if p.fallback)),
        )

    # Final validation before any write: digests, SHAs, JSON, and model syntax.
    for archive, digest in nvim.digests.items():
        if _SHA64.match(digest) is None:
            raise PinUpdateError(f"Invalid digest for {archive}")
    for proposal in proposals.values():
        _validate_sha40(proposal.rev, proposal.name)
    json.loads(new_lock_text)
    compile(new_models, "models.py", "exec")

    (root / "nvim-pack-lock.json").write_text(new_lock_text, encoding="utf-8")
    (root / "src" / "nvim_bundle" / "models.py").write_text(new_models, encoding="utf-8")

    return PinSummary(
        nvim_version=nvim.version,
        nvim_changed=nvim_changed or blink_changed,
        plugin_changes=plugin_changes,
        blink_version=blink_tag,
        blink_changed=blink_changed,
        fallbacks=tuple(sorted(n for n, p in proposals.items() if p.fallback)),
    )


def check_pins(
    root: Path,
    *,
    token: str | None = None,
    api_get=_api_get_json,
    lsremote=_run_lsremote,
) -> tuple[bool, str]:
    """Report drift without writing. Returns (in_sync, report)."""
    token = token if token is not None else _token()
    nvim, proposals, blink_tag = gather_proposals(root, token=token, api_get=api_get, lsremote=lsremote)
    lock = load_lock(root)
    models_text = read_models_text(root)
    new_models = render_models(models_text, nvim.version, nvim.digests)
    if blink_tag is not None:
        from .models import DEFAULT_BLINK_VERSION as current_blink

        if current_blink != blink_tag:
            new_models = re.sub(
                r'^DEFAULT_BLINK_VERSION = "[^"]*"$',
                f'DEFAULT_BLINK_VERSION = "{blink_tag}"',
                new_models,
                count=1,
                flags=re.MULTILINE,
            )
    new_lock_text = render_lock(_lock_with_proposals(lock, proposals))
    old_lock_text = (root / "nvim-pack-lock.json").read_text(encoding="utf-8")
    details: list[str] = []
    if new_models != models_text:
        details.append(f"models.py needs Neovim {nvim.version}")
    for name, proposal in sorted(proposals.items()):
        old_rev = str(lock["plugins"][name].get("rev", ""))
        if old_rev.lower() != proposal.rev.lower():
            if proposal.fallback:
                details.append(f"{name}: {old_rev[:12]} -> {proposal.rev[:12]} (default-branch fallback)")
            elif proposal.tag is not None:
                details.append(f"{name}: {old_rev[:12]} -> {proposal.rev[:12]} ({proposal.tag})")
            else:
                details.append(f"{name}: {old_rev[:12]} -> {proposal.rev[:12]}")
    if new_lock_text != old_lock_text and not details:
        details.append("nvim-pack-lock.json needs deterministic rewrite")
    if not details:
        return True, "pins are in sync"
    lines = ["pin drift detected:"] + [f"- {item}" for item in details]
    if any(p.fallback for p in proposals.values()):
        lines.append("note: fallback entries track default-branch commits, not stable tags")
    return False, "\n".join(lines)
