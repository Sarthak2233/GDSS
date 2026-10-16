"""Targeted static type checking runner for the GDSS validation sandbox."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from gdss.validation.discovery import get_sandbox_timeout, load_validation_config
from gdss.validation.types import TypeCheckResult


def detect_typecheck_command(
    worktree_path: str | Path,
    changed_files: list[str] | None = None,
) -> tuple[str | None, str]:
    """Detect appropriate typechecker command and tool name for the worktree."""
    root = Path(worktree_path)
    config = load_validation_config(root)

    if config.typecheck_command:
        return config.typecheck_command, "config"

    # TypeScript
    if (root / "tsconfig.json").is_file():
        return "tsc --noEmit", "tsc"

    # Python (mypy or pyright if config present)
    if (root / "mypy.ini").is_file() or (root / ".mypy.ini").is_file():
        return "mypy .", "mypy"

    # Rust
    if (root / "Cargo.toml").is_file():
        return "cargo check", "cargo"

    # Go
    if (root / "go.mod").is_file():
        return "go vet ./...", "go"

    return None, "none"


def run_targeted_typecheck(
    worktree_path: str | Path,
    changed_files: list[str] | None = None,
    timeout_seconds: float | None = None,
    custom_command: str | None = None,
) -> TypeCheckResult:
    """Execute targeted type checking within the given worktree sandbox."""
    root = Path(worktree_path)
    config = load_validation_config(root)

    if timeout_seconds is not None and timeout_seconds > 0:
        resolved_timeout = float(timeout_seconds)
    else:
        resolved_timeout = float(get_sandbox_timeout(config_timeout=config.timeout_seconds))

    tool_name = "custom"
    cmd = custom_command

    if not cmd:
        cmd, tool_name = detect_typecheck_command(root, changed_files)

    if not cmd:
        return TypeCheckResult(
            checked=False,
            passed=True,
            tool="none",
            output="No typechecker detected",
        )

    env = dict(os.environ)
    env["CI"] = "true"
    env["GDSS_SANDBOX"] = "true"

    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
            timeout=resolved_timeout,
        )
        output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        passed = proc.returncode == 0
        errors = [line for line in output.splitlines() if "error" in line.lower()]

        return TypeCheckResult(
            checked=True,
            passed=passed,
            tool=tool_name,
            output=output.strip(),
            errors=errors,
        )
    except subprocess.TimeoutExpired:
        return TypeCheckResult(
            checked=True,
            passed=False,
            tool=tool_name,
            output=f"Typecheck timed out after {resolved_timeout}s",
            errors=[f"Timeout ({resolved_timeout}s)"],
        )
    except Exception as exc:
        return TypeCheckResult(
            checked=True,
            passed=False,
            tool=tool_name,
            output=f"Failed to run typechecker: {exc}",
            errors=[str(exc)],
        )
