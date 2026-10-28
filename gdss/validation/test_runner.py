"""Targeted test execution runner for the GDSS validation sandbox."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from gdss.logger import get_logger
from gdss.validation.discovery import get_sandbox_timeout, load_validation_config
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

    # Resolve command
    tool_name = "custom"
    cmd = custom_command

    if not cmd:
        cmd, tool_name = detect_test_command(root, changed_files)

    if not cmd:
        logger.debug("No automated test framework detected for %s", root)
        return TestExecutionResult(
            executed=False,
            passed=True,
            tool="none",
            output="No test runner detected",
        )

    # If changed files are provided, format {test_file} if placeholder exists
    if "{test_file}" in cmd:
        matched = find_targeted_test_files(root, changed_files or [])
        if matched:
            rel_paths = " ".join(str(m.relative_to(root)) for m in matched)
            cmd = cmd.replace("{test_file}", rel_paths)
            logger.debug("Filtered test command with targeted test files: %s", rel_paths)
        else:
            cmd = cmd.replace("{test_file}", "").strip()

    # Sandboxed execution environment
    env = dict(os.environ)
    env["CI"] = "true"
    env["GDSS_SANDBOX"] = "true"

    logger.debug(
        "Running targeted tests with '%s' (cmd: %s, timeout=%.1fs)",
        tool_name,
        cmd,
        resolved_timeout,
    )
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
            logger.info("Targeted tests PASSED with %s (%d passed)", tool_name, tests_passed)
        else:
            logger.warning(
                "Targeted tests FAILED with %s (exit code %d)", tool_name, proc.returncode
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
            "Targeted tests timed out after %.1fs (tool=%s)", resolved_timeout, tool_name
        )
        return TestExecutionResult(
            executed=True,
            passed=False,
            tool=tool_name,
            output=f"Test run timed out after {resolved_timeout}s",
        )
    except Exception as exc:
        logger.warning("Targeted test invocation failed (tool=%s): %s", tool_name, exc)
        return TestExecutionResult(
            executed=True,
            passed=False,
            tool=tool_name,
            output=f"Failed to execute tests: {exc}",
        )
