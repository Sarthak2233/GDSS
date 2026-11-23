"""Targeted test execution runner for the GDSS validation sandbox."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from gdss.logger import get_logger
from gdss.validation.discovery import (
    get_sandbox_timeout,
    group_files_by_package_root,
    load_validation_config,
    prepare_validation_command,
)
from gdss.validation.languages import get_default_registry
from gdss.validation.types import TestExecutionResult

logger = get_logger("gdss.validation.test_runner")
_IGNORED_DIRS = frozenset({"node_modules", "target", "vendor", "__pycache__"})


def find_targeted_test_files(
    worktree_path: str | Path,
    changed_files: list[str],
) -> list[Path]:
    """Identify candidate test files corresponding to changed source files."""
    root = Path(worktree_path)
    registry = get_default_registry()
    matched_test_files: list[Path] = []
    seen: set[Path] = set()

    for changed in changed_files:
        changed_p = Path(changed)
        lang = registry.get_for_file(changed_p)
        if not lang or not lang.test_file_patterns:
            continue

        stem = changed_p.stem
        for pattern in lang.test_file_patterns:
            target_name = pattern.replace("{name}", stem)
            # Search inside worktree for files matching target_name
            for candidate in root.rglob(target_name):
                # Ignore hidden dirs and dependencies
                parts = candidate.parts
                if any(p.startswith(".") or p in _IGNORED_DIRS for p in parts):
                    continue
                if candidate.is_file() and candidate not in seen:
                    seen.add(candidate)
                    matched_test_files.append(candidate)

    return matched_test_files


def detect_test_command(
    worktree_path: str | Path,
    changed_files: list[str] | None = None,
) -> tuple[str | None, str]:
    """Detect appropriate test command and tool name for the worktree."""
    _ = changed_files
    root = Path(worktree_path)
    config = load_validation_config(root)

    # 1. Config override
    if config.test_command:
        return config.test_command, "config"

    # 2. Heuristic detection by project manifests
    if (
        (root / "pyproject.toml").is_file()
        or (root / "setup.py").is_file()
        or (root / "pytest.ini").is_file()
    ):
        return "pytest", "pytest"

    if (root / "package.json").is_file():
        return "npm test", "npm"

    if (root / "Cargo.toml").is_file():
        return "cargo test", "cargo"

    if (root / "go.mod").is_file():
        return "go test ./...", "go"

    # C# / .NET (Solution or Project)
    try:
        if (
            any(root.glob("*.sln"))
            or any(root.glob("*.slnx"))
            or any(root.glob("*.csproj"))
            or any(root.glob("*.fsproj"))
        ):
            return "dotnet test", "dotnet"
    except Exception:
        pass

    # Subpackage check in monorepo if changed_files are provided
    if changed_files:
        pkg_groups = group_files_by_package_root(root, changed_files)
        for pkg_root in pkg_groups:
            if pkg_root != root:
                cmd, tool = detect_test_command(pkg_root)
                if cmd and tool != "none":
                    return cmd, tool

    return None, "none"


def _run_lockfile_sync(cmd: str, root_str: str, env: dict[str, str]) -> bool:
    try:
        logger.info("Synchronizing lockfile in sandbox: %s", cmd)
        subprocess.run(
            cmd,
            shell=True,
            cwd=root_str,
            env=env,
            capture_output=True,
            timeout=30,
            check=False,
        )
        return True
    except Exception as e:
        logger.debug("Sandbox lockfile synchronization failed (%s): %s", cmd, e)
        return False


def synchronize_sandbox_lockfiles(
    worktree_path: str | Path,
    changed_files: list[str] | None = None,
) -> bool:
    """Synchronize lockfiles natively in sandbox when package manifests are changed."""
    if not changed_files:
        return False

    root = Path(worktree_path)
    root_str = str(root)
    env = dict(os.environ)
    env["CI"] = "true"
    env["GDSS_SANDBOX"] = "true"

    changed_names = {Path(f).name for f in changed_files}
    synced = False

    # JavaScript / Node.js
    if "package.json" in changed_names:
        cmd: str | None = None
        if (root / "pnpm-lock.yaml").is_file():
            cmd = "pnpm install --lockfile-only"
        elif (root / "yarn.lock").is_file():
            cmd = "yarn install --mode update-lockfile"
        elif (root / "package-lock.json").is_file() or (root / "package.json").is_file():
            cmd = "npm install --package-lock-only"

        if cmd and _run_lockfile_sync(cmd, root_str, env):
            synced = True

    # Rust
    if "Cargo.toml" in changed_names:
        if (root / "Cargo.lock").is_file() or (root / "Cargo.toml").is_file():
            if _run_lockfile_sync("cargo generate-lockfile", root_str, env):
                synced = True

    # Python Poetry
    if "pyproject.toml" in changed_names and (root / "poetry.lock").is_file():
        if _run_lockfile_sync("poetry lock --no-update", root_str, env):
            synced = True

    return synced


def _run_single_test(
    cwd_path: Path,
    cmd_template: str,
    tool_name: str,
    file_args_list: list[str],
    is_full_suite: bool,
    timeout_seconds: float,
    env: dict[str, str],
) -> TestExecutionResult:
    cmd = cmd_template

    # Mode handling: in full_suite mode, remove placeholder restrictions
    if is_full_suite:
        if "{file}" in cmd:
            cmd = cmd.replace("{file}", "").strip()
        if "{test_file}" in cmd:
            cmd = cmd.replace("{test_file}", "").strip()
    else:
        # If changed files are provided, format {file} if placeholder exists
        if "{file}" in cmd:
            if file_args_list:
                file_args = " ".join(f'"{f}"' for f in file_args_list)
                cmd = cmd.replace("{file}", file_args)
            else:
                cmd = cmd.replace("{file}", ".").strip()

        # If changed files are provided, format {test_file} if placeholder exists
        if "{test_file}" in cmd:
            matched = find_targeted_test_files(cwd_path, file_args_list or [])
            if matched:
                rel_paths = " ".join(
                    f'"{m.relative_to(cwd_path).as_posix()}"'
                    for m in matched
                )
                cmd = cmd.replace("{test_file}", rel_paths)
                logger.debug("Filtered test command with targeted test files in %s: %s", cwd_path, rel_paths)
            else:
                cmd = cmd.replace("{test_file}", "").strip()  # dsa:ignore

    logger.debug(
        "Running tests with '%s' in %s (cmd: %s, timeout=%.1fs)",
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
        # Pytest exit code 5 means 0 tests collected; treat as passed with notice
        is_pytest_zero_tests = proc.returncode == 5 and (
            "pytest" in cmd.lower() or tool_name == "pytest"
        )
        passed = proc.returncode == 0 or is_pytest_zero_tests
        if is_pytest_zero_tests and not output.strip():
            output = "No tests collected (pytest exit code 5)"

        # Basic parse of test results
        tests_passed = 0
        tests_failed = 0
        pass_match = re.search(r"(\d+)\s+passed", output)
        if pass_match:
            tests_passed = int(pass_match.group(1))
        fail_match = re.search(r"(\d+)\s+failed", output)
        if fail_match:
            tests_failed = int(fail_match.group(1))

        tests_run = tests_passed + tests_failed

        if passed:
            logger.info("Targeted tests PASSED with %s in %s (%d passed)", tool_name, cwd_path, tests_passed)
        else:
            logger.warning(
                "Targeted tests FAILED with %s in %s (exit code %d)", tool_name, cwd_path, proc.returncode
            )

        return TestExecutionResult(
            executed=True,
            passed=passed,
            tool=tool_name,
            tests_run=tests_run,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            output=output.strip(),
        )
    except subprocess.TimeoutExpired:
        logger.warning(
            "Targeted tests timed out after %.1fs (tool=%s) in %s", timeout_seconds, tool_name, cwd_path
        )
        return TestExecutionResult(
            executed=True,
            passed=False,
            tool=tool_name,
            output=f"Test run timed out after {timeout_seconds}s in {cwd_path}",
        )
    except Exception as exc:
        logger.warning("Targeted test invocation failed (tool=%s) in %s: %s", tool_name, cwd_path, exc)
        return TestExecutionResult(
            executed=True,
            passed=False,
            tool=tool_name,
            output=f"Failed to execute tests in {cwd_path}: {exc}",
        )


def run_targeted_tests(
    worktree_path: str | Path,
    changed_files: list[str] | None = None,
    timeout_seconds: float | None = None,
    custom_command: str | None = None,
) -> TestExecutionResult:
    """Execute targeted or repository tests within the given worktree sandbox."""
    root = Path(worktree_path)

    if changed_files:
        synchronize_sandbox_lockfiles(root, changed_files)

    config = load_validation_config(root)

    # Resolve timeout: explicit argument -> discovery helper
    if timeout_seconds is not None and timeout_seconds > 0:
        resolved_timeout = float(timeout_seconds)
    else:
        resolved_timeout = float(get_sandbox_timeout(config_timeout=config.timeout_seconds))

    env = dict(os.environ)
    env["CI"] = "true"
    env["GDSS_SANDBOX"] = "true"
    is_full_suite = (config.mode == "full_suite")

    # If explicit custom command is given, execute at root
    if custom_command:
        file_args = changed_files or []
        return _run_single_test(
            cwd_path=root,
            cmd_template=custom_command,
            tool_name="custom",
            file_args_list=file_args,
            is_full_suite=is_full_suite,
            timeout_seconds=resolved_timeout,
            env=env,
        )

    # Monorepo package-aware dispatch
    pkg_groups = group_files_by_package_root(root, changed_files)
    sub_results: list[TestExecutionResult] = []

    for pkg_root, pkg_files in pkg_groups.items():
        cmd, tool_name = detect_test_command(pkg_root, pkg_files)
        if cmd and cmd.strip():
            # Format relative paths to this package root
            rel_files: list[str] = []
            for f in pkg_files:
                try:
                    rel = str((root / f).relative_to(pkg_root))
                    rel_files.append(rel)
                except ValueError:
                    rel_files.append(f)

            res = _run_single_test(
                cwd_path=pkg_root,
                cmd_template=cmd,
                tool_name=tool_name,
                file_args_list=rel_files,
                is_full_suite=is_full_suite,
                timeout_seconds=resolved_timeout,
                env=env,
            )
            sub_results.append(res)

    if not sub_results:
        logger.debug("No automated test framework detected for %s", root)
        return TestExecutionResult(
            executed=False,
            passed=True,
            tool="none",
            output="No test runner detected",
        )

    # Aggregate across all tested packages
    all_passed = all(r.passed for r in sub_results)
    combined_tools = ", ".join(dict.fromkeys(r.tool for r in sub_results if r.tool != "none"))
    combined_outputs = "\n".join(r.output for r in sub_results if r.output and r.output.strip())
    total_passed = sum(r.tests_passed for r in sub_results)
    total_failed = sum(r.tests_failed for r in sub_results)
    total_run = sum(r.tests_run for r in sub_results)

    return TestExecutionResult(
        executed=True,
        passed=all_passed,
        tool=combined_tools or "none",
        tests_run=total_run,
        tests_passed=total_passed,
        tests_failed=total_failed,
        output=combined_outputs.strip(),
    )
