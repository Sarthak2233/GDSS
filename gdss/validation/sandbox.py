"""Validation sandbox facade for verifying candidate merge/convergence patches."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from gdss.validation.syntax import validate_file_syntax
from gdss.validation.test_runner import run_targeted_tests
from gdss.validation.typechecker import run_targeted_typecheck
from gdss.validation.types import (
    SyntaxCheckResult,
    TestExecutionResult,
    TypeCheckResult,
    ValidationReport,
    ValidationStatus,
)
from gdss.validation.worktree import ephemeral_worktree


class ValidationSandbox:
    """Orchestrates candidate patch validation within ephemeral Git worktrees."""

    def __init__(self, repo_path: str | Path) -> None:
        self.repo_path = Path(repo_path).resolve()

    def validate_patch(
        self,
        patch_content: str,
        target_branch: str = "HEAD",
        timeout_seconds: float | None = None,
        run_types: bool = True,
        run_tests: bool = True,
    ) -> ValidationReport:
        """Apply patch to an ephemeral worktree, check syntax, types, and run targeted tests."""
        t0 = time.perf_counter()

        with ephemeral_worktree(self.repo_path, base_ref=target_branch) as wt_path:
            wt_str = str(wt_path)

            def elapsed_ms() -> float:
                return (time.perf_counter() - t0) * 1000  # dsa:ignore

            empty_types = TypeCheckResult(checked=False, passed=True, tool="none")
            empty_tests = TestExecutionResult(executed=False, passed=True, tool="none")
            syntax_clean = SyntaxCheckResult(valid=True, language="ok")

            # 1. Attempt to apply the patch
            apply_proc = subprocess.run(
                ["git", "apply", "--whitespace=fix", "-"],
                cwd=wt_str,
                input=patch_content,
                text=True,
                capture_output=True,
            )
            if apply_proc.returncode != 0:
                err_msg = apply_proc.stderr.strip() or "git apply failed"
                return ValidationReport(
                    status=ValidationStatus.FAILED_PATCH,
                    patch_applied=False,
                    syntax=SyntaxCheckResult(valid=False, language="unknown", error_message=err_msg),
                    types=empty_types,
                    tests=empty_tests,
                    worktree_path=wt_str,
                    duration_ms=elapsed_ms(),  # dsa:ignore
                    error_summary=f"Failed to apply patch: {err_msg}",
                )

            # 2. Identify modified or newly created files
            status_proc = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=wt_str,
                capture_output=True,
                text=True,
            )
            changed_files: list[str] = []
            for line in status_proc.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    target = parts[1].split("->")[-1].strip()
                    changed_files.append(target)

            # 3. Gate 1: Multi-language AST Syntax Check
            for f in changed_files:
                target_file = wt_path / f
                if target_file.is_file():
                    syntax_res = validate_file_syntax(target_file)
                    if not syntax_res.valid:
                        return ValidationReport(
                            status=ValidationStatus.FAILED_SYNTAX,
                            patch_applied=True,
                            syntax=syntax_res,
                            types=empty_types,
                            tests=empty_tests,
                            worktree_path=wt_str,
                            duration_ms=elapsed_ms(),  # dsa:ignore
                            error_summary=f"Syntax error in {f}: {syntax_res.error_message}",
                        )

            # 4. Gate 2: Targeted Static Type Check
            if run_types:
                type_res = run_targeted_typecheck(
                    wt_path,
                    changed_files=changed_files,
                    timeout_seconds=timeout_seconds,
                )
                if type_res.checked and not type_res.passed:
                    return ValidationReport(
                        status=ValidationStatus.FAILED_TYPES,
                        patch_applied=True,
                        syntax=syntax_clean,
                        types=type_res,
                        tests=empty_tests,
                        worktree_path=wt_str,
                        duration_ms=elapsed_ms(),  # dsa:ignore
                        error_summary=f"Type check failed: {type_res.output}",
                    )
            else:
                type_res = TypeCheckResult(checked=False, passed=True, tool="skipped")

            # 5. Gate 3: Targeted Regression Tests
            if run_tests:
                test_res = run_targeted_tests(
                    wt_path,
                    changed_files=changed_files,
                    timeout_seconds=timeout_seconds,
                )
                if test_res.executed and not test_res.passed:
                    return ValidationReport(
                        status=ValidationStatus.FAILED_TESTS,
                        patch_applied=True,
                        syntax=syntax_clean,
                        types=type_res,
                        tests=test_res,
                        worktree_path=wt_str,
                        duration_ms=elapsed_ms(),  # dsa:ignore
                        error_summary=f"Tests failed: {test_res.output}",
                    )
            else:
                test_res = TestExecutionResult(executed=False, passed=True, tool="skipped")

            return ValidationReport(
                status=ValidationStatus.PASSED,
                patch_applied=True,
                syntax=syntax_clean,
                types=type_res,
                tests=test_res,
                worktree_path=wt_str,
                duration_ms=elapsed_ms(),  # dsa:ignore
            )


def validate_patch(
    repo_path: str | Path,
    patch_content: str,
    target_branch: str = "HEAD",
    timeout_seconds: float | None = None,
    run_types: bool = True,
    run_tests: bool = True,
) -> ValidationReport:
    """Convenience helper to validate a patch in an ephemeral worktree sandbox."""
    sandbox = ValidationSandbox(repo_path)
    return sandbox.validate_patch(
        patch_content=patch_content,
        target_branch=target_branch,
        timeout_seconds=timeout_seconds,
        run_types=run_types,
        run_tests=run_tests,
    )
