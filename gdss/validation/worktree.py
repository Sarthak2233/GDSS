"""Ephemeral Git worktree management for isolated validation.

Allows GDSS to execute dry-run candidate patches, syntax compilation,
and test suites without mutating the developer's working directory or index.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

from gdss.logger import get_logger

logger = get_logger("gdss.validation.worktree")

MANIFEST_FILENAMES = frozenset(
    {
        "package.json",
        "pnpm-lock.yaml",
        "package-lock.json",
        "yarn.lock",
        "pyproject.toml",
        "poetry.lock",
        "Pipfile.lock",
        "requirements.txt",
        "Cargo.toml",
        "Cargo.lock",
        "go.mod",
        "go.sum",
    }
)

DEPENDENCY_DIR_NAMES = ("node_modules", ".venv", "vendor")


def symlink_worktree_dependencies(
    parent_repo: Path,
    worktree_path: Path,
    changed_files: Sequence[str] | None = None,
) -> list[Path]:
    """Symlink parent dependency directories into the worktree if manifests are unchanged."""
    if changed_files:
        for f in changed_files:
            name = Path(f).name
            if name in MANIFEST_FILENAMES:
                logger.debug("Skipping dependency symlink: manifest modified (%s)", f)
                return []

    created_links: list[Path] = []
    try:
        resolved_parent = parent_repo.resolve()
        resolved_wt = worktree_path.resolve()
    except Exception:
        resolved_parent = parent_repo
        resolved_wt = worktree_path

    # 1. Root-level dependency directories
    for dep_name in DEPENDENCY_DIR_NAMES:
        parent_dep = resolved_parent / dep_name
        wt_dep = resolved_wt / dep_name
        if parent_dep.is_dir() and not wt_dep.exists() and not wt_dep.is_symlink():
            try:
                os.symlink(parent_dep, wt_dep)
                created_links.append(wt_dep)
                logger.debug("Symlinked %s -> %s", parent_dep, wt_dep)
            except Exception as exc:
                logger.debug("Failed to symlink %s: %s", dep_name, exc)

    # 2. First-level subdirectory dependency directories (e.g. web/node_modules)
    try:
        for sub in resolved_parent.iterdir():
            if sub.is_dir() and not sub.name.startswith("."):
                for dep_name in DEPENDENCY_DIR_NAMES:
                    parent_sub_dep = sub / dep_name
                    wt_sub_dep = resolved_wt / sub.name / dep_name
                    if (
                        parent_sub_dep.is_dir()
                        and (resolved_wt / sub.name).is_dir()
                        and not wt_sub_dep.exists()
                        and not wt_sub_dep.is_symlink()
                    ):
                        try:
                            os.symlink(parent_sub_dep, wt_sub_dep)
                            created_links.append(wt_sub_dep)
                            logger.debug("Symlinked nested %s -> %s", parent_sub_dep, wt_sub_dep)
                        except Exception as exc:
                            logger.debug("Failed to symlink nested %s: %s", wt_sub_dep, exc)
    except Exception as exc:
        logger.debug("Error scanning nested directories for dependency symlinks: %s", exc)

    return created_links


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

    logger.debug("Creating ephemeral worktree at %s for base_ref '%s'", temp_str, base_ref)
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
                logger.info(
                    "Successfully created git worktree at %s (base_ref=%s)", temp_str, base_ref
                )
                yield temp_dir
                return
            logger.warning(
                "git worktree add failed (code %d: %s). Falling back to directory copy.",
                res.returncode,
                res.stderr.strip(),
            )

        # Fallback for non-git or worktree error: shallow copy
        logger.debug("Copying repository to %s for isolated sandbox", temp_str)
        shutil.copytree(
            resolved_repo,
            temp_dir,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(".git", "venv", "node_modules", ".venv"),
        )
        yield temp_dir
    finally:
        if created_worktree:
            logger.debug("Removing git worktree at %s", temp_str)
            subprocess.run(
                ["git", "worktree", "remove", "--force", temp_str],
                cwd=resolved_repo,
                capture_output=True,
                check=False,
            )
        logger.debug("Cleaning up temporary directory %s", temp_str)
        shutil.rmtree(temp_dir, ignore_errors=True)
