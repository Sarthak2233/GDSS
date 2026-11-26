"""Tests for Phase 3: Worktree Dependency Lifecycle & Sandboxing."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from gdss.validation.discovery import load_validation_config
from gdss.validation.sandbox import ValidationSandbox
from gdss.validation.test_runner import run_targeted_tests
from gdss.validation.types import ValidationStatus
from gdss.validation.worktree import symlink_worktree_dependencies


def test_symlink_worktree_dependencies_flat_and_nested(tmp_path: Path) -> None:
    """Verifies that parent dependency directories (node_modules, .venv) are symlinked into worktree."""
    parent_repo = tmp_path / "repo"
    parent_repo.mkdir()
    (parent_repo / "node_modules").mkdir()
    (parent_repo / "node_modules" / "some_pkg").mkdir()
    (parent_repo / "web").mkdir()
    (parent_repo / "web" / "node_modules").mkdir()
    (parent_repo / ".venv").mkdir()

    wt_path = tmp_path / "wt"
    wt_path.mkdir()
    (wt_path / "web").mkdir()

    # When manifests are not modified, symlinks are created
    created = symlink_worktree_dependencies(parent_repo, wt_path, changed_files=["src/index.ts"])
    assert (wt_path / "node_modules").is_symlink() or (
        getattr(os.path, "isjunction", lambda _path: False)(str(wt_path / "node_modules"))
    )
    assert (wt_path / ".venv").is_symlink() or (
        getattr(os.path, "isjunction", lambda _path: False)(str(wt_path / ".venv"))
    )
    assert (wt_path / "web" / "node_modules").is_symlink() or (
        getattr(os.path, "isjunction", lambda _path: False)(
            str(wt_path / "web" / "node_modules")
        )
    )
    assert (wt_path / "node_modules" / "some_pkg").is_dir()
    assert (wt_path / "node_modules").resolve() == (parent_repo / "node_modules").resolve()
    assert len(created) >= 3


def test_symlink_worktree_dependencies_explicit_fallback_skip(tmp_path: Path) -> None:
    parent_repo = tmp_path / "repo"
    parent_repo.mkdir()
    (parent_repo / "node_modules").mkdir()
    wt_path = tmp_path / "wt"
    wt_path.mkdir()

    with patch(
        "gdss.validation.worktree._create_dependency_reuse_link",
        return_value=False,
    ):
        created = symlink_worktree_dependencies(
            parent_repo,
            wt_path,
            changed_files=["src/index.ts"],
        )

    assert created == []
    assert not (wt_path / "node_modules").exists()


def test_symlink_worktree_dependencies_skipped_when_manifest_modified(tmp_path: Path) -> None:
    """Verifies that dependency symlinking is safely bypassed when package.json is modified."""
    parent_repo = tmp_path / "repo"
    parent_repo.mkdir()
    (parent_repo / "node_modules").mkdir()

    wt_path = tmp_path / "wt"
    wt_path.mkdir()

    created = symlink_worktree_dependencies(parent_repo, wt_path, changed_files=["package.json"])
    assert len(created) == 0
    assert not (wt_path / "node_modules").exists()


def test_sandbox_executes_install_command_success_and_failure(tmp_path: Path) -> None:
    """Verifies that ValidationSandbox executes install_command and reports failure if it exits non-zero."""
    # Write .gdss.yml with install_command
    config_file = tmp_path / ".gdss.yml"
    config_file.write_text(
        """
validation:
  install_command: "exit 1"
""",
        encoding="utf-8",
    )
    val_cfg = load_validation_config(tmp_path)
    assert val_cfg.install_command == "exit 1"

    sandbox = ValidationSandbox(tmp_path)
    # Mock ephemeral_worktree to yield tmp_path directly
    with patch("gdss.validation.sandbox.ephemeral_worktree") as mock_wt:
        mock_wt.return_value.__enter__.return_value = tmp_path
        with patch("subprocess.run") as mock_run:
            # 1st call git apply -> returncode 0
            # 2nd call git status -> returncode 0
            # 3rd call install_command -> returncode 1
            mock_run.side_effect = [
                type("Proc", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
                type("Proc", (), {"returncode": 0, "stdout": " M file.py", "stderr": ""})(),
                type("Proc", (), {"returncode": 1, "stdout": "", "stderr": "npm ERR! missing script"})(),
            ]
            rep = sandbox.validate_patch("diff --git a/file.py b/file.py...")
            assert rep.status == ValidationStatus.FAILED_PATCH
            assert "Install command failed" in rep.error_summary


def test_validation_mode_full_suite_vs_targeted(tmp_path: Path) -> None:
    """Verifies that mode: 'full_suite' runs tests without restricting to targeted files."""
    (tmp_path / "pyproject.toml").write_text("[tool.pytest]\n", encoding="utf-8")
    (tmp_path / ".gdss.yml").write_text(
        """
validation:
  mode: "full_suite"
  test_command: "pytest {test_file}"
""",
        encoding="utf-8",
    )
    # In full_suite mode, {test_file} placeholder should be omitted or replaced with empty string
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "1 passed"
        mock_run.return_value.stderr = ""
        res = run_targeted_tests(tmp_path, changed_files=["src/app.py"])
        assert res.passed
        # Check command executed
        cmd_executed = mock_run.call_args[0][0]
        # In full_suite mode, it should not filter to a single targeted test file
        assert "{test_file}" not in cmd_executed
