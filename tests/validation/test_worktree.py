"""Tests for gdss.validation.worktree (Ephemeral Git Worktree Manager)."""

from __future__ import annotations

import subprocess

from gdss.validation.worktree import (
    ephemeral_worktree,
    is_git_repo,
    is_shallow_repo,
)


def _init_test_git_repo(path):
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@gdss.dev"], cwd=path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "GDSS Test"], cwd=path, check=True, capture_output=True
    )
    (path / "file.txt").write_text("initial content\n", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True)


def test_is_git_repo(tmp_path):
    assert is_git_repo(tmp_path) is False
    _init_test_git_repo(tmp_path)
    assert is_git_repo(tmp_path) is True


def test_is_shallow_repo(tmp_path):
    _init_test_git_repo(tmp_path)
    assert is_shallow_repo(tmp_path) is False


def test_ephemeral_worktree_lifecycle_and_cleanup(tmp_path):
    _init_test_git_repo(tmp_path)

    worktree_path = None
    with ephemeral_worktree(tmp_path, "HEAD") as wt:
        worktree_path = wt
        assert wt.is_dir()
        assert (wt / "file.txt").read_text(encoding="utf-8") == "initial content\n"

        # Check that git worktree list lists it
        res = subprocess.run(
            ["git", "worktree", "list"], cwd=tmp_path, capture_output=True, text=True, check=True
        )
        assert str(wt) in res.stdout

        # Mutate inside worktree
        (wt / "file.txt").write_text("modified in sandbox\n", encoding="utf-8")
        assert (tmp_path / "file.txt").read_text(encoding="utf-8") == "initial content\n"

    # After context block exits, worktree must be removed
    assert not worktree_path.exists()
    res = subprocess.run(
        ["git", "worktree", "list"], cwd=tmp_path, capture_output=True, text=True, check=True
    )
    assert str(worktree_path) not in res.stdout


def test_ephemeral_worktree_cleanup_on_exception(tmp_path):
    _init_test_git_repo(tmp_path)

    worktree_path = None
    try:
        with ephemeral_worktree(tmp_path, "HEAD") as wt:
            worktree_path = wt
            assert wt.is_dir()
            raise RuntimeError("Simulated failure in test")
    except RuntimeError:
        pass

    assert worktree_path is not None
    assert not worktree_path.exists()
    res = subprocess.run(
        ["git", "worktree", "list"], cwd=tmp_path, capture_output=True, text=True, check=True
    )
    assert str(worktree_path) not in res.stdout
