from __future__ import annotations

import shutil
from pathlib import Path

from .models import Target
from .runtime import BuildError, environment, require_tools, run


SOURCE_HINTS = {
    "markdown": "tree-sitter-markdown",
    "markdown_inline": "tree-sitter-markdown-inline",
    "tsx": "tsx",
    "typescript": "typescript",
    "xml": "xml",
}


def languages_from(path: Path) -> list[str]:
    languages = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    languages = [language for language in languages if language]
    if not languages:
        raise BuildError(f"Tree-sitter language list is empty: {path}")
    return languages


def find_parser_source(project_dir: Path, language: str) -> Path:
    hint = SOURCE_HINTS.get(language)
    if hint:
        candidate = project_dir / hint / "src" / "parser.c"
        if candidate.is_file():
            return candidate
    candidates = sorted(
        path
        for path in project_dir.rglob("parser.c")
        if path.parent.name == "src" and path.is_file()
    )
    if not candidates:
        raise BuildError(f"Missing parser source for {language} under {project_dir}")
    return candidates[0]


def find_scanner_source(source_dir: Path) -> Path | None:
    for name in ("scanner.c", "scanner.cc", "scanner.cpp"):
        candidate = source_dir / name
        if candidate.is_file():
            return candidate
    return None


def build_treesitter(
    root: Path,
    stage: Path,
    target: Target,
    *,
    source: str,
    max_jobs: int | None,
) -> None:
    require_tools("git", "nvim", "tree-sitter")
    ts_dir = stage / ".build" / "nvim-treesitter"
    revision = (root / "build" / "nvim-treesitter.rev").read_text(encoding="utf-8").strip()
    cache_dir = stage / ".build" / "cache"
    languages_file = root / "build" / "treesitter-languages.txt"
    build_script = root / "scripts" / "build_treesitter.lua"

    (stage / ".build").mkdir(parents=True, exist_ok=True)
    run(["git", "clone", "--filter=blob:none", "--no-checkout", source, ts_dir])
    run(["git", "-C", ts_dir, "fetch", "--depth=1", "origin", revision])
    run(["git", "-C", ts_dir, "checkout", "--detach", "--quiet", revision])

    runtime = stage / "runtime"
    (runtime / "parser").mkdir(parents=True, exist_ok=True)
    (runtime / "queries").mkdir(parents=True, exist_ok=True)
    env = environment(
        XDG_CACHE_HOME=cache_dir,
        TREESITTER_PLUGIN_DIR=ts_dir,
        TREESITTER_INSTALL_DIR=runtime,
        TREESITTER_LANGUAGES_FILE=languages_file,
        TREESITTER_MAX_JOBS=str(max_jobs) if max_jobs is not None else None,
    )
    if max_jobs is None:
        env.pop("TREESITTER_MAX_JOBS", None)
    run(["nvim", "--headless", "-i", "NONE", "-u", "NONE", "-l", build_script], env=env)

    if target.zig_target:
        cross_compile_treesitter(stage, target, languages_file)


def cross_compile_treesitter(stage: Path, target: Target, language_file: Path) -> None:
    if target.zig_target is None:
        return
    require_tools("zig")
    cache_dir = stage / ".build" / "cache" / "nvim"
    install_dir = stage / "runtime" / "parser"
    languages = languages_from(language_file)

    cc = ["zig", "cc", "-target", target.zig_target]
    cxx = ["zig", "c++", "-target", target.zig_target]
    for language in languages:
        project_dir = cache_dir / f"tree-sitter-{language}"
        parser_source = find_parser_source(project_dir, language)
        source_dir = parser_source.parent
        object_dir = stage / ".build" / "cross" / language
        shutil.rmtree(object_dir, ignore_errors=True)
        object_dir.mkdir(parents=True, exist_ok=True)
        parser_object = object_dir / "parser.o"
        run(cc + ["-O2", "-fPIC", "-std=c11", "-I", source_dir, "-c", parser_source, "-o", parser_object])
        objects = [parser_object]
        linker = cc

        scanner_source = find_scanner_source(source_dir)
        if scanner_source:
            scanner_object = object_dir / "scanner.o"
            if scanner_source.suffix == ".c":
                run(cc + ["-O2", "-fPIC", "-std=c11", "-I", source_dir, "-c", scanner_source, "-o", scanner_object])
            else:
                run(cxx + ["-O2", "-fPIC", "-I", source_dir, "-c", scanner_source, "-o", scanner_object])
                linker = cxx
            objects.append(scanner_object)

        install_dir.mkdir(parents=True, exist_ok=True)
        output = install_dir / f"{language}.so"
        temporary = Path(f"{output}.tmp")
        run(linker + ["-shared", *objects, "-o", temporary])
        temporary.replace(output)
        validate_architecture(output, target, language)
        print(f"Built {language} for {target.zig_target}")


def validate_architecture(output: Path, target: Target, language: str) -> None:
    if shutil.which("readelf") is None:
        return
    result = run(["readelf", "-h", output], capture_output=True)
    machine = next(
        (line.split(":", 1)[1].strip() for line in result.stdout.splitlines() if line.startswith("  Machine:")),
        "",
    )
    expected = "X86-64" if target.name.startswith("linux-x86_64-") else "AArch64"
    if expected.lower() not in machine.lower():
        raise BuildError(f"Unexpected parser architecture for {language}: {machine}")
