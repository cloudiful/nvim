from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .download import sha256_file
from .models import Target
from .runtime import BuildError
from .tool_staging import _asset


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    kind: str
    version: str
    asset: str | None = None
    package: str | None = None
    entry: str | None = None
    source_name: str | None = None
    preserve_runtime: bool = False
    runtime_asset: str | None = None


TOOL_DEFINITIONS = (
    ToolDefinition("stylua", "formatter", "2.5.2", asset="stylua", source_name="stylua"),
    ToolDefinition(
        "rustfmt", "formatter", "1.9.0", asset="rustfmt", source_name="rustfmt",
        runtime_asset="rustc-runtime",
    ),
    ToolDefinition("gofmt", "formatter", "go1.25.12", asset="gofmt", source_name="gofmt"),
    ToolDefinition("shfmt", "formatter", "3.13.1", asset="shfmt", source_name="shfmt"),
    ToolDefinition("prettier", "formatter", "3.9.6", package="prettier", entry="bin/prettier.cjs"),
    ToolDefinition("prettierd", "formatter", "0.29.0", package="@fsouza/prettierd", entry="bin/prettierd"),
    ToolDefinition(
        "lua-language-server", "lsp", "3.18.2", asset="lua-language-server",
        source_name="lua-language-server", preserve_runtime=True,
    ),
    ToolDefinition("rust-analyzer", "lsp", "2026-07-27", asset="rust-analyzer", source_name="rust-analyzer"),
    ToolDefinition("bash-language-server", "lsp", "5.6.0", package="bash-language-server", entry="out/cli.js"),
    ToolDefinition("docker-langserver", "lsp", "0.15.0", package="dockerfile-language-server-nodejs", entry="bin/docker-langserver"),
    ToolDefinition("docker-compose-langserver", "lsp", "0.5.0", package="@microsoft/compose-language-service", entry="bin/docker-compose-langserver"),
    ToolDefinition("vscode-json-language-server", "lsp", "4.10.0", package="vscode-langservers-extracted", entry="bin/vscode-json-language-server"),
    ToolDefinition("yaml-language-server", "lsp", "1.24.0", package="yaml-language-server", entry="bin/yaml-language-server"),
    ToolDefinition("vscode-css-language-server", "lsp", "4.10.0", package="vscode-langservers-extracted", entry="bin/vscode-css-language-server"),
    ToolDefinition("tombi", "lsp", "1.2.4", asset="tombi", source_name="tombi"),
    ToolDefinition("vtsls", "lsp", "0.3.0", package="@vtsls/language-server", entry="bin/vtsls.js"),
    ToolDefinition("vue-language-server", "lsp", "3.3.8", package="@vue/language-server", entry="bin/vue-language-server.js"),
    ToolDefinition("@vue/typescript-plugin", "runtime", "3.3.8", package="@vue/typescript-plugin"),
    ToolDefinition("node", "runtime", "22.17.0", asset="node", source_name="node"),
)

EXTERNAL_TOOLS = {
    "jdtls": "Java remains an external dependency",
    "java": "Java 21 or newer remains an external dependency",
    "maven": "Maven remains an external project dependency",
    "gradle": "Gradle remains an external project dependency",
    "nu": "Nushell LSP remains an external dependency",
    "hyprls": "Hyprland LSP remains an external dependency",
}


def load_asset_config(root: Path) -> dict:
    path = root / "build" / "tool-assets.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildError(f"Invalid tool asset configuration: {path}") from exc
    if config.get("schema_version") != 1:
        raise BuildError(f"Unsupported tool asset schema: {path}")
    for entry in config.get("assets", {}).values():
        for asset in entry.get("targets", {}).values():
            _validate_sha256(asset.get("sha256"), "tool asset")
    for package in config.get("node_packages", []):
        _validate_sha256(package.get("sha256"), package.get("name", "Node package"))
    return config


def _validate_sha256(value: str | None, label: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
        raise BuildError(f"Invalid SHA-256 for {label}")


def parse_manifest(path: Path) -> dict:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildError(f"Invalid tool manifest: {path}") from exc
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != 1
        or manifest.get("profile") != "full"
        or not isinstance(manifest.get("target"), str)
        or not isinstance(manifest.get("tools"), dict)
    ):
        raise BuildError(f"Unsupported tool manifest: {path}")
    for name, tool in manifest["tools"].items():
        if not isinstance(tool, dict):
            raise BuildError(f"Invalid tool manifest entry: {name}")
        if tool.get("status") not in {"bundled", "external", "unsupported"}:
            raise BuildError(f"Invalid status for {name}: {tool.get('status')}")
        if tool.get("status") != "bundled":
            continue
        if not tool.get("path") or not tool.get("version"):
            raise BuildError(f"Bundled tool is missing path/version: {name}")
        relative_path = Path(tool["path"])
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise BuildError(f"Bundled tool path escapes the bundle: {name}")
        _validate_sha256(tool.get("source_sha256"), f"{name} source")
        if "runtime_source_sha256" in tool:
            _validate_sha256(tool["runtime_source_sha256"], f"{name} runtime source")
    return manifest


def tool_statuses(root: Path, target: Target) -> dict[str, str]:
    assets = load_asset_config(root)["assets"]
    node_available = target.tool_target in assets["node"]["targets"]
    statuses: dict[str, str] = {}
    for definition in TOOL_DEFINITIONS:
        if definition.name == "node":
            statuses[definition.name] = "bundled" if node_available else "external"
        elif definition.package:
            statuses[definition.name] = "bundled" if node_available else "external"
        elif definition.asset and target.tool_target in assets[definition.asset]["targets"]:
            statuses[definition.name] = "bundled"
        else:
            statuses[definition.name] = "unsupported"
    statuses.update({name: "external" for name in EXTERNAL_TOOLS})
    return statuses


def _manifest(root: Path, stage: Path, target: Target, config: dict, paths: dict[str, Path]) -> dict:
    statuses = tool_statuses(root, target)
    package_sources = {item["name"]: item for item in config["node_packages"]}
    result = {"schema_version": 1, "profile": "full", "target": target.name, "tools": {}}
    for definition in TOOL_DEFINITIONS:
        item = {"status": statuses[definition.name], "version": definition.version}
        if definition.name in paths:
            path = paths[definition.name]
            item["path"] = str(path.relative_to(stage)).replace(os.sep, "/")
            if path.is_file():
                item["sha256"] = sha256_file(path)
            if definition.asset:
                asset = _asset(config, definition.asset, target)
                item["source_url"] = asset["url"]
                item["source_sha256"] = asset["sha256"]
            if definition.package:
                package = package_sources[definition.package]
                item["source_url"] = package["url"]
                item["source_sha256"] = package["sha256"]
            if definition.runtime_asset:
                runtime_asset = _asset(config, definition.runtime_asset, target)
                if runtime_asset is not None:
                    item["runtime_source_url"] = runtime_asset["url"]
                    item["runtime_source_sha256"] = runtime_asset["sha256"]
        elif definition.package:
            item["reason"] = "Node runtime is not bundled for this target"
        else:
            item["reason"] = "No compatible release asset for this target"
        result["tools"][definition.name] = item
    for name, reason in EXTERNAL_TOOLS.items():
        result["tools"][name] = {"status": "external", "reason": reason}
    return result


def stage_full_tools(root: Path, stage: Path, target: Target) -> dict:
    from .tool_staging import stage_native, stage_node, stage_node_wrappers

    config = load_asset_config(root)
    cache = stage / ".build" / "tool-cache"
    cache.mkdir(parents=True, exist_ok=True)
    paths = stage_node(stage, target, config, cache)
    if paths:
        paths.update(stage_node_wrappers(stage, config, target, TOOL_DEFINITIONS))
        plugin = stage / ".runtime" / "node_modules" / "@vue" / "typescript-plugin"
        if plugin.is_dir():
            paths["@vue/typescript-plugin"] = plugin
    for definition in TOOL_DEFINITIONS:
        if not definition.asset or definition.name == "node":
            continue
        asset = _asset(config, definition.asset, target)
        if asset is not None:
            paths[definition.name] = stage_native(stage, target, definition, asset, config, cache)
    manifest = _manifest(root, stage, target, config, paths)
    (stage / "tool-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest
