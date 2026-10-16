"""Tests for gdss.validation.sandbox (ValidationSandbox Facade)."""
from __future__ import annotations

from pathlib import Path

from git import Repo

from gdss.validation.sandbox import validate_patch
from gdss.validation.types import ValidationStatus


def _init_test_git_repo(tmp_path: Path) -> Repo:
    repo = Repo.init(tmp_path)
    # Configure author
    with repo.config_writer() as config:
        config.set_value("user", "name", "GDSS Test")
        config.set_value("user", "email", "test@gdss.dev")

    # Initial file and commit
    hello_file = tmp_path / "hello.py"
    hello_file.write_text("def hello() -> str:\n    return 'hello'\n", encoding="utf-8")
    repo.index.add(["hello.py"])
    repo.index.commit("Initial commit")
    return repo


def test_validate_clean_patch_passes(tmp_path: Path):
    _init_test_git_repo(tmp_path)

    # Patch modifying hello.py with valid code
    patch = (
        "diff --git a/hello.py b/hello.py\n"
        "--- a/hello.py\n"
        "+++ b/hello.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def hello() -> str:\n"
        "-    return 'hello'\n"
        "+    return 'world'\n"
    )

    report = validate_patch(tmp_path, patch)
    assert report.status == ValidationStatus.PASSED
    assert report.patch_applied is True
    assert report.is_clean is True
    assert report.syntax.valid is True
    assert report.duration_ms >= 0


def test_validate_invalid_patch_fails_patch_gate(tmp_path: Path):
    _init_test_git_repo(tmp_path)

    # Malformed patch that cannot apply
    corrupt_patch = (
        "diff --git a/hello.py b/hello.py\n"
        "--- a/hello.py\n"
        "+++ b/hello.py\n"
        "@@ -99,1 +99,1 @@\n"
        "-nonexistent\n"
        "+bad\n"
    )

    report = validate_patch(tmp_path, corrupt_patch)
    assert report.status == ValidationStatus.FAILED_PATCH
    assert report.patch_applied is False
    assert report.is_clean is False


def test_validate_syntax_error_fails_syntax_gate(tmp_path: Path):
    _init_test_git_repo(tmp_path)

    bad_syntax_patch = (
        "diff --git a/hello.py b/hello.py\n"
        "--- a/hello.py\n"
        "+++ b/hello.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def hello() -> str:\n"
        "-    return 'hello'\n"
        "+    return (broken syntax\n"
    )

    report = validate_patch(tmp_path, bad_syntax_patch)
    assert report.status == ValidationStatus.FAILED_SYNTAX
    assert report.patch_applied is True
    assert report.is_clean is False
    assert report.syntax.valid is False
    assert report.syntax.language == "python"


def test_validate_test_failure_fails_tests_gate(tmp_path: Path):
    repo = _init_test_git_repo(tmp_path)

    # Add config with a failing test command
    cfg = tmp_path / ".gdss.yml"
    cfg.write_text(
        "validation:\n  test_command: python -c 'import sys; sys.exit(1)'\n",
        encoding="utf-8",
    )
    repo.index.add([".gdss.yml"])
    repo.index.commit("Add config")

    valid_patch = (
        "diff --git a/hello.py b/hello.py\n"
        "--- a/hello.py\n"
        "+++ b/hello.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def hello() -> str:\n"
        "-    return 'hello'\n"
        "+    return 'world'\n"
    )

    report = validate_patch(tmp_path, valid_patch)
    assert report.status == ValidationStatus.FAILED_TESTS
    assert report.patch_applied is True
    assert report.is_clean is False
    assert report.tests.passed is False
