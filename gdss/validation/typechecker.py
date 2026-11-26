"""Targeted static type checking runner for the GDSS validation sandbox."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from gdss.logger import get_logger
from gdss.validation.discovery import (
    get_sandbox_timeout,
    group_files_by_package_root,
    load_validation_config,
    prepare_validation_command,
)
from gdss.validation.types import TypeCheckResult

logger = get_logger("gdss.validation.typecheck")


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

    # C# / .NET (Solution or Project)
    try:
        if (
            any(root.glob("*.sln"))
            or any(root.glob("*.slnx"))
            or any(root.glob("*.csproj"))
            or any(root.glob("*.fsproj"))
        ):
            return "dotnet build --no-incremental", "dotnet"
    except Exception:
        pass

    # Subpackage check in monorepo if changed_files are provided
    if changed_files:
        pkg_groups = group_files_by_package_root(root, changed_files)
        for pkg_root in pkg_groups:
            if pkg_root != root:
                cmd, tool = detect_typecheck_command(pkg_root)
                if cmd and tool != "none":
                    return cmd, tool

    return None, "none"


def _run_single_typecheck(
    cwd_path: Path,
    cmd_template: str,
    tool_name: str,
    file_args_list: list[str],
    timeout_seconds: float,
    env: dict[str, str],
) -> TypeCheckResult:
    cmd = cmd_template
    if "{file}" in cmd:
        if file_args_list:
            formatted_files = " ".join(f'"{f}"' for f in file_args_list)
            cmd = cmd.replace("{file}", formatted_files)
        else:
            cmd = cmd.replace("{file}", ".").strip()

    logger.debug(
        "Running typechecker '%s' in %s (command: %s, timeout=%.1fs)",
        tool_name,
        cwd_path,
        cmd,
        timeout_seconds,
    )
    try:
        prepared_cmd = prepare_validation_command(cmd)
        proc = subprocess.run(
            prepared_cmd,
            shell=not isinstance(prepared_cmd, list),
            cwd=str(cwd_path),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
        passed = proc.returncode == 0
        errors = [line for line in output.splitlines() if "error" in line.lower()]

        if passed:
            logger.debug("Typecheck passed with tool '%s' in %s", tool_name, cwd_path)
        else:
            logger.warning("Typecheck failed (tool=%s, exit_code=%d)", tool_name, proc.returncode)

        return TypeCheckResult(
            checked=True,
            passed=passed,
            tool=tool_name,
            output=output.strip(),
            errors=errors,
        )
    except subprocess.TimeoutExpired:
        logger.warning("Typecheck timed out after %.1fs (tool=%s)", timeout_seconds, tool_name)
        return TypeCheckResult(
            checked=True,
            passed=False,
            tool=tool_name,
            output=f"Typecheck timed out after {timeout_seconds}s",
            errors=[f"Timeout ({timeout_seconds}s)"],
        )
    except Exception as exc:
        logger.warning("Typecheck invocation failed (tool=%s): %s", tool_name, exc)
        return TypeCheckResult(
            checked=True,
            passed=False,
            tool=tool_name,
            output=f"Failed to run typechecker: {exc}",
            errors=[str(exc)],
        )


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

    env = dict(os.environ)
    env["CI"] = "true"
    env["GDSS_SANDBOX"] = "true"

    # If an explicit custom command is given, execute at root
    if custom_command:
        file_args = changed_files or []
        return _run_single_typecheck(
            cwd_path=root,
            cmd_template=custom_command,
            tool_name="custom",
            file_args_list=file_args,
            timeout_seconds=resolved_timeout,
            env=env,
        )

    # Monorepo package-aware dispatch
    pkg_groups = group_files_by_package_root(root, changed_files)
    sub_results: list[TypeCheckResult] = []

    for pkg_root, pkg_files in pkg_groups.items():
        cmd, tool_name = detect_typecheck_command(pkg_root, pkg_files)
        if cmd and cmd.strip():
            # Format relative paths to this package root
            rel_files: list[str] = []
            for f in pkg_files:
                try:
                    rel = str((root / f).relative_to(pkg_root))
                    rel_files.append(rel.replace("\\", "/"))
                except ValueError:
                    rel_files.append(f)

            res = _run_single_typecheck(
                cwd_path=pkg_root,
                cmd_template=cmd,
                tool_name=tool_name,
                file_args_list=rel_files,
                timeout_seconds=resolved_timeout,
                env=env,
            )
            sub_results.append(res)

    if not sub_results:
        logger.debug("No static typechecker detected for %s", root)
        return TypeCheckResult(
            checked=False,
            passed=True,
            tool="none",
            output="No typechecker detected",
        )

    # Aggregate across all tested packages
    all_passed = all(r.passed for r in sub_results)
    combined_tools = ", ".join(dict.fromkeys(r.tool for r in sub_results if r.tool != "none"))
    combined_outputs = "\n".join(r.output for r in sub_results if r.output and r.output.strip())
    combined_errors = [e for r in sub_results for e in r.errors]

    return TypeCheckResult(
        checked=True,
        passed=all_passed,
        tool=combined_tools or "none",
        output=combined_outputs.strip(),
        errors=combined_errors,
    )
