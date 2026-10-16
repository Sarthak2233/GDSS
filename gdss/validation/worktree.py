"""Ephemeral Git worktree management for isolated validation.

Allows GDSS to execute dry-run candidate patches, syntax compilation,
and test suites without mutating the developer's working directory or index.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def is_git_repo(path: Path) -> bool:
    """Check if the given path is within a valid git work tree."""
    res = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=path,
        capture_output=True,
        text=True,
        check=False,
    )
    return res.returncode == 0 and res.stdout.strip() == "true"


def is_shallow_repo(path: Path) -> bool:
    """Check if the repository is a shallow clone (e.g. CI runner default)."""
    res = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=path,
        capture_output=True,
        text=True,
        check=False,
    )
    return res.returncode == 0 and res.stdout.strip() == "true"


@contextmanager
def ephemeral_worktree(repo_path: Path, base_ref: str = "HEAD") -> Iterator[Path]:
    """Create an ephemeral, detached git worktree in a temporary directory.

    Guarantees clean removal and pruning upon exit, even if an exception occurs.
    Falls back to a temporary directory copy if the environment cannot support worktrees.
    """
    resolved_repo = repo_path.resolve()
    temp_dir = Path(tempfile.mkdtemp(prefix="gdss-worktree-"))
    temp_str = str(temp_dir)
    created_worktree = False

    try:
        if is_git_repo(resolved_repo):
            cmd = ["git", "worktree", "add", "--detach", temp_str, base_ref]
            res = subprocess.run(
                cmd,
                cwd=resolved_repo,
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                created_worktree = True
                yield temp_dir
                return

        # Fallback for non-git or worktree error: shallow copy
        shutil.copytree(resolved_repo, temp_dir, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".git", "venv", "node_modules", ".venv"))
        yield temp_dir
    finally:
        if created_worktree:
            subprocess.run(
                ["git", "worktree", "remove", "--force", temp_str],
                cwd=resolved_repo,
                capture_output=True,
                check=False,
            )
        shutil.rmtree(temp_dir, ignore_errors=True)
