"""Tests for gdss.validation.guarded_apply (Human-Approved Patch Apply)."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from gdss.cli.main import app
from gdss.validation.guarded_apply import (
    apply_suggestion,
    preflight_check,
    rollback_suggestion,
)


@pytest.fixture
def dummy_git_repo(tmp_path: Path) -> tuple[Path, str]:
    """Create a minimal real git repo with a test file and initial commit."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test Agent"], cwd=repo_dir, check=True)

    auth_file = repo_dir / "auth.py"
    auth_file.write_text(
        "def login(user: str) -> bool:\n"
        "    timeout = 10\n"
        "    return bool(user)\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True)

    head_rev = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return repo_dir, head_rev


@pytest.fixture
def sample_suggestion_data(dummy_git_repo: tuple[Path, str]) -> dict[str, Any]:
    _, head_sha = dummy_git_repo
    return {
        "id": "sug_test123",
        "file_path": "auth.py",
        "line_start": 1,
        "line_end": 4,
        "symbol_id": "auth.py::login",
        "target_commit": head_sha,
        "patch_combinations": [
            {
                "label": "increase_timeout",
                "strategy": "keep_left",
                "patch_text": (
                    "--- a/auth.py\n"
                    "+++ b/auth.py\n"
                    "@@ -1,3 +1,3 @@\n"
                    " def login(user: str) -> bool:\n"
                    "-    timeout = 10\n"
                    "+    timeout = 30\n"
                    "     return bool(user)\n"
                ),
                "validated": True,
                "validation_status": "validated",
            }
        ],
    }


def test_preflight_passes_for_fresh_valid_suggestion(
    dummy_git_repo: tuple[Path, str],
    sample_suggestion_data: dict[str, Any],
):
    repo_dir, head_sha = dummy_git_repo
    res = preflight_check(
        suggestion_data=sample_suggestion_data,
        repo_root=repo_dir,
        current_head_sha=head_sha,
    )
    assert res.valid is True
    assert res.target_file == repo_dir / "auth.py"
    assert res.strategy == "keep_left"
    assert res.error is None


def test_preflight_fails_on_stale_commit(
    dummy_git_repo: tuple[Path, str],
    sample_suggestion_data: dict[str, Any],
):
    repo_dir, head_sha = dummy_git_repo
    stale_data = dict(sample_suggestion_data)
    stale_data["target_commit"] = "0000000000000000000000000000000000000000"

    res = preflight_check(
        suggestion_data=stale_data,
        repo_root=repo_dir,
        current_head_sha=head_sha,
    )
    assert res.valid is False
    assert "stale" in res.what.lower()
    assert "WHAT:" in (res.error or "")
    assert "WHY:" in (res.error or "")
    assert "FIX:" in (res.error or "")


def test_preflight_fails_on_path_traversal(
    dummy_git_repo: tuple[Path, str],
    sample_suggestion_data: dict[str, Any],
):
    repo_dir, head_sha = dummy_git_repo
    traversal_data = dict(sample_suggestion_data)
    traversal_data["file_path"] = "../../etc/passwd"

    res = preflight_check(
        suggestion_data=traversal_data,
        repo_root=repo_dir,
        current_head_sha=head_sha,
    )
    assert res.valid is False
    assert "traversal" in res.what.lower() or "outside repository" in res.what.lower()


def test_preflight_fails_on_missing_symbol(
    dummy_git_repo: tuple[Path, str],
    sample_suggestion_data: dict[str, Any],
):
    repo_dir, head_sha = dummy_git_repo
    missing_sym_data = dict(sample_suggestion_data)
    missing_sym_data["symbol_id"] = "auth.py::non_existent_function"

    res = preflight_check(
        suggestion_data=missing_sym_data,
        repo_root=repo_dir,
        current_head_sha=head_sha,
    )
    assert res.valid is False
    assert "symbol" in res.what.lower()


def test_atomic_apply_dry_run(
    dummy_git_repo: tuple[Path, str],
    sample_suggestion_data: dict[str, Any],
):
    repo_dir, _ = dummy_git_repo
    # Save suggestion to store
    sug_dir = repo_dir / ".gdss" / "suggestions"
    sug_dir.mkdir(parents=True, exist_ok=True)
    import json
    (sug_dir / "sug_test123.json").write_text(json.dumps(sample_suggestion_data), encoding="utf-8")

    res = apply_suggestion(
        suggestion_id="sug_test123",
        repo_root=repo_dir,
        dry_run=True,
    )
    assert res.success is True
    assert "-    timeout = 10" in res.diff
    assert "+    timeout = 30" in res.diff

    # Verify original file on disk was NOT modified
    auth_file = repo_dir / "auth.py"
    assert "timeout = 10" in auth_file.read_text(encoding="utf-8")


def test_atomic_apply_success(
    dummy_git_repo: tuple[Path, str],
    sample_suggestion_data: dict[str, Any],
):
    repo_dir, _ = dummy_git_repo
    sug_dir = repo_dir / ".gdss" / "suggestions"
    sug_dir.mkdir(parents=True, exist_ok=True)
    import json
    (sug_dir / "sug_test123.json").write_text(json.dumps(sample_suggestion_data), encoding="utf-8")

    res = apply_suggestion(
        suggestion_id="sug_test123",
        repo_root=repo_dir,
        dry_run=False,
    )
    assert res.success is True
    assert res.rollback_id == "sug_test123"

    # Verify file on disk was modified
    auth_file = repo_dir / "auth.py"
    content = auth_file.read_text(encoding="utf-8")
    assert "timeout = 30" in content
    assert "timeout = 10" not in content

    # Verify rollback record was created
    rollback_file = repo_dir / ".gdss" / "rollback" / "sug_test123.json"
    assert rollback_file.is_file()


def test_atomic_apply_syntax_failure_triggers_automatic_rollback(
    dummy_git_repo: tuple[Path, str],
    sample_suggestion_data: dict[str, Any],
):
    repo_dir, _ = dummy_git_repo
    broken_sug = dict(sample_suggestion_data)
    broken_sug["id"] = "sug_broken"
    broken_sug["patch_combinations"] = [
        {
            "label": "broken_syntax",
            "strategy": "bad",
            "patch_text": (
                "--- a/auth.py\n"
                "+++ b/auth.py\n"
                "@@ -1,3 +1,3 @@\n"
                " def login(user: str) -> bool:\n"
                "-    timeout = 10\n"
                "+    timeout = = 30\n"
                "     return bool(user)\n"
            ),
            "validated": True,
            "validation_status": "validated",
        }
    ]
    sug_dir = repo_dir / ".gdss" / "suggestions"
    sug_dir.mkdir(parents=True, exist_ok=True)
    import json
    (sug_dir / "sug_broken.json").write_text(json.dumps(broken_sug), encoding="utf-8")

    res = apply_suggestion(
        suggestion_id="sug_broken",
        repo_root=repo_dir,
        dry_run=False,
    )
    assert res.success is False
    assert "syntax" in res.what.lower()
    assert "rolled back" in res.fix.lower()

    # Original file must be completely intact
    auth_file = repo_dir / "auth.py"
    assert "timeout = 10" in auth_file.read_text(encoding="utf-8")


def test_manual_rollback_command(
    dummy_git_repo: tuple[Path, str],
    sample_suggestion_data: dict[str, Any],
):
    repo_dir, _ = dummy_git_repo
    sug_dir = repo_dir / ".gdss" / "suggestions"
    sug_dir.mkdir(parents=True, exist_ok=True)
    import json
    (sug_dir / "sug_test123.json").write_text(json.dumps(sample_suggestion_data), encoding="utf-8")

    # 1. Apply
    apply_res = apply_suggestion(
        suggestion_id="sug_test123",
        repo_root=repo_dir,
        dry_run=False,
    )
    assert apply_res.success is True
    auth_file = repo_dir / "auth.py"
    assert "timeout = 30" in auth_file.read_text(encoding="utf-8")

    # 2. Rollback
    rb_res = rollback_suggestion(
        suggestion_id="sug_test123",
        repo_root=repo_dir,
    )
    assert rb_res.success is True
    assert rb_res.restored is True

    # 3. Verify original content restored
    assert "timeout = 10" in auth_file.read_text(encoding="utf-8")

    # 4. Rollback file should be removed
    rollback_file = repo_dir / ".gdss" / "rollback" / "sug_test123.json"
    assert not rollback_file.exists()


def test_cli_apply_dry_run_and_execution(
    dummy_git_repo: tuple[Path, str],
    sample_suggestion_data: dict[str, Any],
):
    runner = CliRunner()
    repo_dir, _ = dummy_git_repo
    sug_dir = repo_dir / ".gdss" / "suggestions"
    sug_dir.mkdir(parents=True, exist_ok=True)
    import json
    (sug_dir / "sug_test123.json").write_text(json.dumps(sample_suggestion_data), encoding="utf-8")

    # 1. CLI Help
    res_help = runner.invoke(app, ["apply", "--help"])
    assert res_help.exit_code == 0
    assert "--strategy" in res_help.output
    assert "--dry-run" in res_help.output
    assert "--rollback" in res_help.output

    # 2. CLI Dry-Run
    res_dry = runner.invoke(app, ["apply", "sug_test123", "--repo", str(repo_dir), "--dry-run"])
    assert res_dry.exit_code == 0
    assert "DRY RUN" in res_dry.output
    auth_file = repo_dir / "auth.py"
    assert "timeout = 10" in auth_file.read_text(encoding="utf-8")

    # 3. CLI Apply
    res_apply = runner.invoke(app, ["apply", "sug_test123", "--repo", str(repo_dir)])
    assert res_apply.exit_code == 0
    assert "Successfully applied" in res_apply.output
    assert "timeout = 30" in auth_file.read_text(encoding="utf-8")

    # 4. CLI Rollback
    res_rb = runner.invoke(app, ["apply", "sug_test123", "--repo", str(repo_dir), "--rollback"])
    assert res_rb.exit_code == 0
    assert "Successfully restored" in res_rb.output
    assert "timeout = 10" in auth_file.read_text(encoding="utf-8")


