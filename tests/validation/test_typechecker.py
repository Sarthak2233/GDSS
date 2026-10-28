"""Tests for gdss.validation.typechecker (Targeted Type Checking)."""

from __future__ import annotations

from pathlib import Path

from gdss.validation.typechecker import run_targeted_typecheck
from gdss.validation.types import TypeCheckResult


def test_no_typechecker_detected(tmp_path: Path):
    res = run_targeted_typecheck(tmp_path)
    assert isinstance(res, TypeCheckResult)
    assert res.checked is False
    assert res.passed is True
    assert res.tool == "none"


def test_custom_typecheck_command_success(tmp_path: Path):
    res = run_targeted_typecheck(
        tmp_path,
        custom_command="python -c 'print(\"Types valid!\")'",
    )
    assert res.checked is True
    assert res.passed is True
    assert res.output is not None
    assert "Types valid!" in res.output


def test_custom_typecheck_command_failure(tmp_path: Path):
    res = run_targeted_typecheck(
        tmp_path,
        custom_command="python -c 'import sys; sys.stderr.write(\"Type error at line 4\\n\"); sys.exit(1)'",
    )
    assert res.checked is True
    assert res.passed is False
    assert res.output is not None
    assert "Type error" in res.output


def test_config_typecheck_command_override(tmp_path: Path):
    config_file = tmp_path / ".gdss.yml"
    config_file.write_text(
        "validation:\n  typecheck_command: python -c 'print(\"config typecheck\")'\n",
        encoding="utf-8",
    )
    res = run_targeted_typecheck(tmp_path)
    assert res.checked is True
    assert res.passed is True
    assert res.output is not None
    assert "config typecheck" in res.output
