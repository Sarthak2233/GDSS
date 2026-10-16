"""Repository layout discovery and validation configuration parser.

Allows GDSS validation to remain completely agnostic of repository layout
(flat repos, multi-service directories, monorepos, Bazel, etc.).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# Standard project descriptor files across major ecosystems
PROJECT_DESCRIPTORS = {
    # Python
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
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

        if current == resolved_repo or current.parent == current:
            break
        try:
            current.relative_to(resolved_repo)
        except ValueError:
            break
        current = current.parent

    return repo_root


def load_validation_config(repo_root: Path) -> ValidationConfig:
    """Load configuration from .gdss.yml or .gdss.yaml in repo_root if present."""
    default_config = ValidationConfig()
    config_file = repo_root / ".gdss.yml"
    has_config = config_file.is_file()
    if not has_config:
        config_file = repo_root / ".gdss.yaml"
        has_config = config_file.is_file()  # dsa:ignore

    if not has_config:
        return default_config

    try:
        data = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
    except Exception:
        return default_config

    val_data: dict[str, Any] = data.get("validation", {})
    if not isinstance(val_data, dict):
        val_data = {}

    return ValidationConfig(
        test_command=val_data.get("test_command"),
        typecheck_command=val_data.get("typecheck_command"),
        syntax_command=val_data.get("syntax_command"),
        timeout_seconds=int(val_data.get("timeout_seconds", 30)),
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
