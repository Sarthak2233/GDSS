"""Tests for Phase 1 remediation of validation layer and configuration bugs."""

from __future__ import annotations

import subprocess
from pathlib import Path

from gdss.validation.pr_audit import load_radar_config
from gdss.validation.sandbox import ValidationSandbox
from gdss.validation.test_runner import run_targeted_tests
from gdss.validation.typechecker import run_targeted_typecheck
from gdss.validation.types import ValidationStatus


def test_typechecker_replaces_file_placeholder(tmp_path: Path) -> None:
    """Confirms run_targeted_typecheck substitutes {file} with actual changed file path."""
    sample_file = tmp_path / "sample.py"
    sample_file.write_text("x: int = 1\n", encoding="utf-8")

    # Command expects the filename 'sample.py' as the argument.
    # If {file} is literal, sys.argv[1] is '{file}' and exits with code 1.
    cmd = 'python3 -c "import sys; sys.exit(0 if \'sample.py\' in sys.argv[1] else 1)" {file}'
    res = run_targeted_typecheck(
        tmp_path,
        changed_files=["sample.py"],
        custom_command=cmd,
    )
    assert res.checked is True
    assert res.passed is True, f"Failed output: {res.output}"


def test_test_runner_replaces_file_placeholder(tmp_path: Path) -> None:
    """Confirms run_targeted_tests substitutes {file} with actual changed file path."""
    sample_file = tmp_path / "sample.py"
    sample_file.write_text("def test_ok(): pass\n", encoding="utf-8")

    cmd = 'python3 -c "import sys; sys.exit(0 if \'sample.py\' in sys.argv[1] else 1)" {file}'
    res = run_targeted_tests(
        tmp_path,
        changed_files=["sample.py"],
        custom_command=cmd,
    )
    assert res.executed is True
    assert res.passed is True, f"Failed output: {res.output}"


def test_pytest_exit_code_5_handled_as_passed(tmp_path: Path) -> None:
    """Confirms pytest exit code 5 (no tests collected) is treated as passed."""
    # Command named pytest that exits with code 5 and outputs pytest-style no tests message
    cmd = 'python3 -c "import sys; print(\'collected 0 items\'); sys.exit(5)" # pytest'
    res = run_targeted_tests(
        tmp_path,
        changed_files=["sample.py"],
        custom_command=cmd,
    )
    assert res.executed is True
    assert res.passed is True
    assert "No tests collected" in res.output or "collected 0 items" in res.output


def test_pr_audit_loads_concurrency_and_condensation(tmp_path: Path) -> None:
    """Confirms load_radar_config parses concurrency_limit and condensation from .gdss.yml."""
    config_file = tmp_path / ".gdss.yml"
    config_file.write_text(
        """
radar:
  model: "gpt-4o"
  concurrency_limit: 8
  condensation: "ast_minimal"
""",
        encoding="utf-8",
    )

    cfg = load_radar_config(tmp_path)
    assert cfg.get("concurrency_limit") == 8
    assert cfg.get("condensation") == "ast_minimal"


def test_sandbox_executes_syntax_command_failure_and_success(tmp_path: Path) -> None:
    """Confirms ValidationSandbox Gate 1 executes validation.syntax_command."""
    # Create git repo in tmp_path
    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(tmp_path), check=True)

    test_file = tmp_path / "hello.py"
    test_file.write_text("print('hello')\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), check=True)

    # 1. Test failing syntax command
    failing_yml = tmp_path / ".gdss.yml"
    failing_yml.write_text(
        """
validation:
  syntax_command: "python3 -c 'import sys; sys.exit(1)' {file}"
""",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "commit", "-m", "add config"], cwd=str(tmp_path), check=True)

    sandbox = ValidationSandbox(tmp_path)
    patch_content = """--- a/hello.py
+++ b/hello.py
@@ -1,1 +1,1 @@
-print('hello')
+print('world')
"""
    report = sandbox.validate_patch(patch_content, run_types=False, run_tests=False)
    assert report.status == ValidationStatus.FAILED_SYNTAX
    assert "Syntax command failed" in report.error_summary

    # 2. Test passing syntax command
    failing_yml.write_text(
        """
validation:
  syntax_command: "python3 -c 'import sys; sys.exit(0)' {file}"
""",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "commit", "-m", "update config"], cwd=str(tmp_path), check=True)

    report2 = sandbox.validate_patch(patch_content, run_types=False, run_tests=False)
    assert report2.status == ValidationStatus.PASSED


def test_get_sandbox_timeout_precedence(monkeypatch) -> None:
    """Verifies CLI, env var, and config timeout precedence."""
    from gdss.validation.discovery import get_sandbox_timeout

    # 1. Default when nothing set
    monkeypatch.delenv("GDSS_SANDBOX_TIMEOUT", raising=False)
    assert get_sandbox_timeout(config_timeout=None, cli_timeout=None) == 30

    # 2. Config timeout respected when CLI is None
    assert get_sandbox_timeout(config_timeout=45, cli_timeout=None) == 45

    # 3. Env var overrides config timeout
    monkeypatch.setenv("GDSS_SANDBOX_TIMEOUT", "60")
    assert get_sandbox_timeout(config_timeout=45, cli_timeout=None) == 60

    # 4. Explicit CLI flag overrides everything
    assert get_sandbox_timeout(config_timeout=45, cli_timeout=90) == 90

