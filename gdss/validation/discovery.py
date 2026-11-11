"""Repository layout discovery and validation configuration parser.

Allows GDSS validation to remain completely agnostic of repository layout
(flat repos, multi-service directories, monorepos, Bazel, etc.).
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

# Standard project descriptor files across major ecosystems
PROJECT_DESCRIPTORS = {
    # Python
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
    "pytest.ini",
    "mypy.ini",
    ".mypy.ini",
    # JavaScript / TypeScript
    "package.json",
    "tsconfig.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    # Rust
    "Cargo.toml",
    # Go
    "go.mod",
    # Java / Kotlin
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    # C / C++
    "CMakeLists.txt",
    "Makefile",
}


@dataclass(frozen=True)
class ValidationConfig:
    """Explicit repository-level configuration for the validation sandbox."""

    test_command: str | None = None
    typecheck_command: str | None = None
    syntax_command: str | None = None
    install_command: str | None = None
    mode: str = "targeted"
    symlink_dependencies: bool = True
    timeout_seconds: int = 30


def find_project_root_for_file(file_path: Path, repo_root: Path) -> Path:
    """Walk upward from file_path to find the nearest project descriptor directory.

    Falls back to repo_root if no specific project descriptor is encountered.
    """
    try:
        resolved_file = file_path.resolve()
        resolved_repo = repo_root.resolve()
    except Exception:
        resolved_file = file_path
        resolved_repo = repo_root

    current = resolved_file.parent
    while True:
        for descriptor in PROJECT_DESCRIPTORS:
            if (current / descriptor).is_file():
                return current

        # Check for .NET project / solution files (*.csproj, *.fsproj, *.sln)
        try:
            if any(current.glob("*.csproj")) or any(current.glob("*.sln")) or any(current.glob("*.fsproj")):
                return current
        except Exception:
            pass

        if current == resolved_repo or current.parent == current:
            break
        try:
            current.relative_to(resolved_repo)
        except ValueError:
            break
        current = current.parent

    return repo_root


def group_files_by_package_root(
    repo_root: Path,
    changed_files: Sequence[str] | None = None,
) -> dict[Path, list[str]]:
    """Group relative changed files by their nearest enclosing project descriptor directory.

    Returns a dictionary mapping package_root Path -> list of changed files (paths relative to repo_root).
    If changed_files is empty or None, returns {repo_root: []}.
    """
    try:
        resolved_repo = repo_root.resolve()
    except Exception:
        resolved_repo = repo_root

    if not changed_files:
        return {resolved_repo: []}

    groups: dict[Path, list[str]] = {}
    for f in changed_files:
        file_path = resolved_repo / f
        pkg_root = find_project_root_for_file(file_path, resolved_repo)
        if pkg_root not in groups:
            groups[pkg_root] = []
        groups[pkg_root].append(f)

    return groups


def load_validation_config(repo_root: Path | str) -> ValidationConfig:
    """Load configuration from .gdss.yml or .gdss.yaml in repo_root if present."""
    from gdss.core.config import load_gdss_config

    cfg = load_gdss_config(repo_root)
    return ValidationConfig(
        test_command=cfg.validation.test_command,
        typecheck_command=cfg.validation.typecheck_command,
        syntax_command=cfg.validation.syntax_command,
        install_command=cfg.validation.install_command,
        mode=cfg.validation.mode,
        symlink_dependencies=cfg.validation.symlink_dependencies,
        timeout_seconds=cfg.validation.timeout_seconds,
    )


def get_sandbox_timeout(
    config_timeout: int | None = None,
    cli_timeout: int | None = None,
) -> int:
    """Resolve sandbox execution timeout.

    Precedence:
    1. CLI flag (--sandbox-timeout)
    2. Environment variable GDSS_SANDBOX_TIMEOUT
    3. Configuration file (.gdss.yml timeout_seconds)
    4. Default 30 seconds
    """
    if cli_timeout is not None and cli_timeout > 0:
        return cli_timeout

    env_val = os.getenv("GDSS_SANDBOX_TIMEOUT")
    if env_val:
        try:
            val = int(env_val.strip())
            if val > 0:
                return val
        except ValueError:
            pass

    if config_timeout is not None and config_timeout > 0:
        return config_timeout

    return 30
