"""Tests for Phase 4: Monorepo & Multi-Package Intelligence."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from gdss.validation.discovery import group_files_by_package_root
from gdss.validation.test_runner import detect_test_command, run_targeted_tests
from gdss.validation.typechecker import detect_typecheck_command, run_targeted_typecheck


def test_group_files_by_package_root_multi_package(tmp_path: Path) -> None:
    """Verifies that changed files are grouped into their respective package roots."""
    repo_root = tmp_path
    # web subpackage
    web_dir = repo_root / "web"
    web_dir.mkdir()
    (web_dir / "package.json").write_text('{"name": "web"}', encoding="utf-8")

    # backend subpackage
    backend_dir = repo_root / "backend"
    backend_dir.mkdir()
    (backend_dir / "pyproject.toml").write_text("[tool.pytest]\n", encoding="utf-8")

    changed_files = [
        "web/src/components/Button.tsx",
        "web/src/App.tsx",
        "backend/app/auth.py",
        "README.md",
    ]

    groups = group_files_by_package_root(repo_root, changed_files)
    assert web_dir in groups
    assert backend_dir in groups
    assert repo_root in groups

    assert groups[web_dir] == ["web/src/components/Button.tsx", "web/src/App.tsx"]
    assert groups[backend_dir] == ["backend/app/auth.py"]
    assert groups[repo_root] == ["README.md"]


def test_monorepo_typechecker_detects_subdirectory_tsconfig(tmp_path: Path) -> None:
    """Verifies that typechecker detects web/tsconfig.json when root has no tsconfig."""
    repo_root = tmp_path
    web_dir = repo_root / "web"
    web_dir.mkdir()
    (web_dir / "tsconfig.json").write_text("{}", encoding="utf-8")

    cmd, tool = detect_typecheck_command(repo_root, changed_files=["web/src/Button.tsx"])
    assert cmd == "tsc --noEmit"
    assert tool == "tsc"


def test_monorepo_test_runner_detects_subdirectory_pytest(tmp_path: Path) -> None:
    """Verifies that test runner detects backend/pyproject.toml when root has no pyproject."""
    repo_root = tmp_path
    backend_dir = repo_root / "backend"
    backend_dir.mkdir()
    (backend_dir / "pyproject.toml").write_text("[tool.pytest]\n", encoding="utf-8")

    cmd, tool = detect_test_command(repo_root, changed_files=["backend/app/main.py"])
    assert cmd == "pytest"
    assert tool == "pytest"


def test_monorepo_typechecker_runs_in_subpackage_cwd(tmp_path: Path) -> None:
    """Verifies that run_targeted_typecheck executes with cwd set to the subpackage."""
    repo_root = tmp_path
    web_dir = repo_root / "web"
    web_dir.mkdir()
    (web_dir / "tsconfig.json").write_text("{}", encoding="utf-8")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Typecheck passed"
        mock_run.return_value.stderr = ""

        res = run_targeted_typecheck(repo_root, changed_files=["web/src/Button.tsx"])
        assert res.passed
        assert mock_run.call_count == 1
        # Crucial: cwd must be web_dir!
        assert mock_run.call_args[1]["cwd"] == str(web_dir)


def test_monorepo_test_runner_runs_in_subpackage_cwd(tmp_path: Path) -> None:
    """Verifies that run_targeted_tests executes with cwd set to the subpackage."""
    repo_root = tmp_path
    backend_dir = repo_root / "backend"
    backend_dir.mkdir()
    (backend_dir / "pyproject.toml").write_text("[tool.pytest]\n", encoding="utf-8")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "1 passed"
        mock_run.return_value.stderr = ""

        res = run_targeted_tests(repo_root, changed_files=["backend/app/main.py"])
        assert res.passed
        assert mock_run.call_count == 1
        # Crucial: cwd must be backend_dir!
        assert mock_run.call_args[1]["cwd"] == str(backend_dir)


def test_monorepo_multi_package_aggregate_reporting(tmp_path: Path) -> None:
    """Verifies that if one package passes and another fails, the aggregate fails with both outputs."""
    repo_root = tmp_path
    web_dir = repo_root / "web"
    web_dir.mkdir()
    (web_dir / "tsconfig.json").write_text("{}", encoding="utf-8")

    backend_dir = repo_root / "backend"
    backend_dir.mkdir()
    (backend_dir / "mypy.ini").write_text("[mypy]\n", encoding="utf-8")

    changed_files = ["web/src/Button.tsx", "backend/app/main.py"]

    with patch("subprocess.run") as mock_run:
        # 1st call (web) passes, 2nd call (backend) fails with error
        mock_run.side_effect = [
            type("Proc", (), {"returncode": 0, "stdout": "web: success", "stderr": ""})(),
            type("Proc", (), {"returncode": 1, "stdout": "", "stderr": "backend: error: incompatible type"})(),
        ]

        res = run_targeted_typecheck(repo_root, changed_files=changed_files)
        assert res.checked is True
        assert res.passed is False
        assert "backend: error: incompatible type" in res.output


def test_package_scoped_file_substitution(tmp_path: Path) -> None:
    """Verifies that {file} placeholder is formatted relative to the package cwd."""
    repo_root = tmp_path
    web_dir = repo_root / "web"
    web_dir.mkdir()
    (web_dir / "tsconfig.json").write_text("{}", encoding="utf-8")
    (web_dir / ".gdss.yml").write_text(
        """
validation:
  typecheck_command: "tsc {file}"
""",
        encoding="utf-8",
    )

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Typecheck passed"
        mock_run.return_value.stderr = ""

        res = run_targeted_typecheck(repo_root, changed_files=["web/src/Button.tsx"])
        assert res.passed
        assert mock_run.call_count == 1
        cmd_executed = mock_run.call_args[0][0]
        # Should be "src/Button.tsx" (relative to web_dir), not "web/src/Button.tsx"
        assert 'tsc "src/Button.tsx"' == cmd_executed
