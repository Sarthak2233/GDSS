"""Tests for gdss.validation.sandbox (ValidationSandbox Facade)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from git import Repo

from gdss.ai.patch_parser import replacement_to_unified_diff
from gdss.core.transform_types import OperatorType, SemanticOperator
from gdss.validation.pr_audit import generate_pr_convergence_patch
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


def test_convergence_patch_validation_is_ephemeral_and_preserves_repository(tmp_path: Path):
    repo = _init_test_git_repo(tmp_path)

    checkout = tmp_path / "checkout.py"
    checkout.write_text(
        "def process_payment(user, card):\n"
        "    return True\n\n"
        "def checkout(user, card):\n"
        "    return process_payment(user, card)\n",
        encoding="utf-8",
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_checkout.py").write_text(
        "from checkout import checkout\n\n"
        "def test_checkout_adapts_old_call():\n"
        "    assert checkout('u', 'c') is True\n",
        encoding="utf-8",
    )
    (tmp_path / ".gdss.yml").write_text(
        """
version: 1
radar:
  risk_threshold: 0.1
  fail_on_collision: false
validation:
  mode: "targeted"
  symlink_dependencies: false
  syntax_command: "python -m py_compile {file}"
  typecheck_command: 'python -c "raise SystemExit(0)"'
  test_command: "python -m pytest {test_file}"
  timeout_seconds: 60
""",
        encoding="utf-8",
    )
    repo.index.add(["checkout.py", "tests/test_checkout.py", ".gdss.yml"])
    repo.index.commit("Add caller and convergence validation fixture")

    before_head = repo.head.commit.hexsha
    before_branch = repo.active_branch.name
    before_index = repo.git.diff("--cached", "--stat")
    before_worktree = repo.git.diff("--stat")
    before_status = repo.git.status("--porcelain")
    before_content = checkout.read_text(encoding="utf-8")

    current_op = SemanticOperator(
        operator=OperatorType.MODIFY_FUNCTION,
        file="checkout.py",
        name="process_payment",
        details={
            "signature_changed": True,
            "old_signature": "(user, card)",
            "new_signature": "(user)",
        },
    )
    other_op = SemanticOperator(
        operator=OperatorType.MODIFY_FUNCTION,
        file="checkout.py",
        name="checkout",
    )
    valid_replacement = (
        "def process_payment(user):\n"
        "    return True\n\n"
        "def checkout(user, card):\n"
        "    return process_payment(user)\n"
    )

    with patch(
        "gdss.ai.openai_provider.OpenAICompatibleProvider.complete",
        return_value=valid_replacement,
    ):
        generated = generate_pr_convergence_patch(
            repo_path=tmp_path,
            target_file="checkout.py",
            overlapping_symbol="process_payment",
            current_ops=[current_op],
            other_ops=[other_op],
            token="external-test-token",
            model="test-model",
        )

    assert generated is not None
    patch_text = replacement_to_unified_diff(
        generated,
        before_content,
        "checkout.py",
        1,
    )
    assert patch_text

    valid_report = validate_patch(tmp_path, patch_text)
    assert valid_report.is_clean
    assert valid_report.status == ValidationStatus.PASSED
    assert valid_report.patch_applied is True
    assert valid_report.syntax.valid is True
    assert valid_report.types.checked is True
    assert valid_report.types.passed is True
    assert valid_report.tests.executed is True
    assert valid_report.tests.passed is True
    assert valid_report.worktree_path is not None
    assert not Path(valid_report.worktree_path).exists()

    invalid_replacement = "def checkout(user, card):\n    return (broken\n"
    invalid_patch = replacement_to_unified_diff(
        invalid_replacement,
        before_content,
        "checkout.py",
        1,
    )
    invalid_report = validate_patch(tmp_path, invalid_patch)
    assert invalid_report.is_clean is False
    assert invalid_report.status == ValidationStatus.FAILED_SYNTAX
    assert invalid_report.syntax.valid is False
    assert invalid_report.worktree_path is not None
    assert not Path(invalid_report.worktree_path).exists()

    assert repo.head.commit.hexsha == before_head
    assert repo.active_branch.name == before_branch
    assert repo.git.diff("--cached", "--stat") == before_index
    assert repo.git.diff("--stat") == before_worktree
    assert repo.git.status("--porcelain") == before_status
    assert checkout.read_text(encoding="utf-8") == before_content
