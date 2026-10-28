"""Result types and statuses for the GDSS validation sandbox."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ValidationStatus(str, Enum):
    """Overall status of a sandboxed patch validation run."""

    PASSED = "PASSED"
    FAILED_PATCH = "FAILED_PATCH"
    FAILED_SYNTAX = "FAILED_SYNTAX"
    FAILED_TYPES = "FAILED_TYPES"
    FAILED_TESTS = "FAILED_TESTS"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True)
class SyntaxCheckResult:
    """Outcome of language-specific syntax/AST compilation."""

    valid: bool
    language: str
    error_message: str | None = None
    line_number: int | None = None


@dataclass(frozen=True)
class TypeCheckResult:
    """Outcome of targeted static typechecker execution."""

    checked: bool
    passed: bool
    tool: str
    output: str | None = None
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TestExecutionResult:
    """Outcome of targeted test execution against candidate patch."""

    __test__ = False

    executed: bool
    passed: bool
    tool: str
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    output: str | None = None
    failed_test_names: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ValidationReport:
    """Comprehensive validation evidence report for a candidate patch."""

    status: ValidationStatus
    patch_applied: bool
    syntax: SyntaxCheckResult
    types: TypeCheckResult
    tests: TestExecutionResult
    worktree_path: str | None = None
    duration_ms: float = 0.0
    error_summary: str | None = None

    @property
    def is_clean(self) -> bool:
        """Returns True if the patch passed all executed validation gates."""
        return self.status == ValidationStatus.PASSED
