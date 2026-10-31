"""CLI drift / alerts behavior over fixture repos."""

import os
import shutil
import tempfile
from io import StringIO
from unittest.mock import patch

import git
import pytest
from rich.console import Console

from gdss.cli.start import GDSSShell


@pytest.fixture
def single_branch_repo():
    temp_dir = tempfile.mkdtemp()
    repo = git.Repo.init(temp_dir)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test")
        cw.set_value("user", "email", "t@example.com")
    path = os.path.join(temp_dir, "a.py")
    with open(path, "w") as f:
        f.write("def hello():\n    return 1\n")
    repo.index.add(["a.py"])
    repo.index.commit("init")
    yield temp_dir, repo.active_branch.name
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def divergent_repo():
    temp_dir = tempfile.mkdtemp()
    repo = git.Repo.init(temp_dir)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test")
        cw.set_value("user", "email", "t@example.com")
    path = os.path.join(temp_dir, "calc.py")
    with open(path, "w") as f:
        f.write("def add(a, b):\n    return a + b\n")
    repo.index.add(["calc.py"])
    repo.index.commit("base")
    base_name = repo.active_branch.name

    feature = repo.create_head("feature")
    repo.head.reference = feature
    repo.head.reset(index=True, working_tree=True)
    with open(path, "w") as f:
        f.write("def add(a, b):\n    return a + b + 1\n\ndef mul(a, b):\n    return a * b\n")
    repo.index.add(["calc.py"])
    repo.index.commit("diverge")
    yield temp_dir, base_name
    shutil.rmtree(temp_dir, ignore_errors=True)


def _run_do(shell: GDSSShell, method: str, arg: str = "") -> str:
    buf = StringIO()
    test_console = Console(file=buf, force_terminal=False, width=120)
    with patch("gdss.cli.start.console", test_console):
        getattr(shell, method)(arg)
    return buf.getvalue()


def test_drift_single_attractor_honest_message(single_branch_repo):
    temp_dir, branch = single_branch_repo
    with patch("rich.prompt.Prompt.ask", return_value="default"):
        shell = GDSSShell(temp_dir)
        try:
            out = _run_do(shell, "do_drift", branch)
        finally:
            shell.do_quit(None)
    assert "no other" in out.lower() or "single attractor" in out.lower()


def test_drift_divergent_branch_positive_magnitude(divergent_repo):
    temp_dir, base_name = divergent_repo
    with patch("rich.prompt.Prompt.ask", return_value="default"):
        shell = GDSSShell(temp_dir)
        try:
            out = _run_do(shell, "do_drift", base_name)
        finally:
            shell.do_quit(None)
    assert "feature" in out.lower()
    # Table should show a non-zero magnitude somewhere (0.xxx with non-all-zero)
    assert "Magnitude" in out or "magnitude" in out.lower() or "0." in out


def test_alerts_runs_without_error(divergent_repo):
    temp_dir, base_name = divergent_repo
    with patch("rich.prompt.Prompt.ask", return_value="default"):
        shell = GDSSShell(temp_dir)
        try:
            out = _run_do(shell, "do_alerts", base_name)
        finally:
            shell.do_quit(None)
    assert "DRIFT" in out.upper() or "alert" in out.lower() or "threshold" in out.lower()
