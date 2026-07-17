"""Public-behavior checks for status labeling helpers."""

import os
import shutil
import tempfile

import git
import pytest

from gdss.core.trajectory import is_single_attractor_trajectory
from gdss.watcher.git_observer import GitObserver


@pytest.fixture
def single_branch_repo():
    temp_dir = tempfile.mkdtemp()
    repo = git.Repo.init(temp_dir)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test")
        cw.set_value("user", "email", "t@example.com")
    path = os.path.join(temp_dir, "a.py")
    with open(path, "w") as f:
        f.write("x = 1\n")
    repo.index.add(["a.py"])
    repo.index.commit("init")
    yield temp_dir, repo.active_branch.name
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_single_attractor_detected(single_branch_repo):
    temp_dir, branch = single_branch_repo
    observer = GitObserver(temp_dir)
    ok, name = is_single_attractor_trajectory(observer, branch)
    assert ok is True
    assert name == branch


def test_remote_status_label_never_says_drift(single_branch_repo):
    temp_dir, branch = single_branch_repo
    observer = GitObserver(temp_dir)
    status = observer.get_remote_sync_status(branch)
    assert "DRIFT" not in str(status["label"]).upper()
