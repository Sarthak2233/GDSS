"""Tests for gdss.validation.types data structures."""
from __future__ import annotations

from gdss.validation.types import (
    SyntaxCheckResult,
    TestExecutionResult,
    TypeCheckResult,
    ValidationReport,
    ValidationStatus,
)


def test_validation_status_enum():
    assert ValidationStatus.PASSED.value == "PASSED"
    assert ValidationStatus.FAILED_PATCH.value == "FAILED_PATCH"
    assert ValidationStatus.FAILED_SYNTAX.value == "FAILED_SYNTAX"
    assert ValidationStatus.FAILED_TYPES.value == "FAILED_TYPES"
    assert ValidationStatus.FAILED_TESTS.value == "FAILED_TESTS"


def test_syntax_check_result():
    res = SyntaxCheckResult(valid=True, language="python")
    assert res.valid is True
    assert res.language == "python"
    assert res.error_message is None

    err = SyntaxCheckResult(
        valid=False,
        language="python",
        error_message="unexpected EOF",
        line_number=42,
    )
    assert err.valid is False
    assert err.line_number == 42


def test_type_check_result():
    res = TypeCheckResult(checked=True, passed=True, tool="mypy")
    assert res.checked is True
    assert res.passed is True
    assert len(res.errors) == 0

    err = TypeCheckResult(
        checked=True,
        passed=False,
        tool="mypy",
        output="Incompatible return type",
        errors=["Incompatible return type [services/auth.py:15]"],
    )
    assert err.passed is False
    assert len(err.errors) == 1


def test_test_execution_result():
    res = TestExecutionResult(
        executed=True,
        passed=True,
        tool="pytest",
        tests_run=5,
        tests_passed=5,
        tests_failed=0,
    )
    assert res.passed is True
    assert res.tests_run == 5

    failed = TestExecutionResult(
        executed=True,
        passed=False,
        tool="pytest",
        tests_run=3,
        tests_passed=2,
        tests_failed=1,
        failed_test_names=["test_login_timeout"],
    )
    assert failed.passed is False
    assert failed.failed_test_names == ["test_login_timeout"]


def test_validation_report_properties():
    report = ValidationReport(
        status=ValidationStatus.PASSED,
        patch_applied=True,
        syntax=SyntaxCheckResult(valid=True, language="python"),
        types=TypeCheckResult(checked=True, passed=True, tool="mypy"),
        tests=TestExecutionResult(
            executed=True,
            passed=True,
            tool="pytest",
            tests_run=2,
            tests_passed=2,
            tests_failed=0,
        ),
    )
    assert report.is_clean is True
    assert report.status == ValidationStatus.PASSED

    failed_report = ValidationReport(
        status=ValidationStatus.FAILED_SYNTAX,
        patch_applied=True,
        syntax=SyntaxCheckResult(
            valid=False,
            language="python",
            error_message="syntax error",
            line_number=10,
        ),
        types=TypeCheckResult(checked=False, passed=True, tool="none"),
        tests=TestExecutionResult(executed=False, passed=True, tool="none"),
        error_summary="Syntax error at line 10",
    )
    assert failed_report.is_clean is False
    assert failed_report.error_summary == "Syntax error at line 10"
