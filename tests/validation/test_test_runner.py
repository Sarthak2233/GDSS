"""Tests for gdss.validation.test_runner (Targeted Test Execution)."""

from __future__ import annotations

from pathlib import Path

from gdss.validation.test_runner import find_targeted_test_files, run_targeted_tests
from gdss.validation.types import TestExecutionResult


def test_no_test_runner_detected(tmp_path: Path):
    res = run_targeted_tests(tmp_path)
    assert isinstance(res, TestExecutionResult)
    assert res.executed is False
    assert res.passed is True
    assert res.tool == "none"


def test_custom_command_execution_success(tmp_path: Path):
    res = run_targeted_tests(
        tmp_path,
        custom_command="python -c 'print(\"Tests passed!\")'",
    )
    assert res.executed is True
    assert res.passed is True
    assert res.output is not None
    assert "Tests passed!" in res.output


def test_custom_command_execution_failure(tmp_path: Path):
    res = run_targeted_tests(
        tmp_path,
        custom_command="python -c 'import sys; sys.stderr.write(\"Fatal error\\n\"); sys.exit(2)'",
    )
    assert res.executed is True
    assert res.passed is False
    assert res.output is not None
    assert "Fatal error" in res.output


def test_timeout_handling(tmp_path: Path):
    res = run_targeted_tests(
        tmp_path,
        custom_command="python -c 'import time; time.sleep(2)'",
        timeout_seconds=0.1,
    )
    assert res.executed is True
    assert res.passed is False
    assert res.output is not None
    assert "timed out" in res.output.lower()


def test_find_targeted_test_files(tmp_path: Path):
    # Setup repo structure: src/calc.py and tests/test_calc.py
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    calc_file = src_dir / "calc.py"
    calc_file.write_text("def add(a, b): return a + b\n")

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_calc = tests_dir / "test_calc.py"
    test_calc.write_text("def test_add(): assert True\n")

    found = find_targeted_test_files(tmp_path, ["src/calc.py"])
    assert len(found) == 1
    assert found[0].name == "test_calc.py"


def test_config_file_test_command_override(tmp_path: Path):
    # Write .gdss.yml with custom test command
    config_file = tmp_path / ".gdss.yml"
    config_file.write_text(
        "validation:\n  test_command: python -c 'print(\"custom ran\")'\n",
        encoding="utf-8",
    )

    res = run_targeted_tests(tmp_path)
    assert res.executed is True
    assert res.passed is True
    assert res.output is not None
    assert "custom ran" in res.output
