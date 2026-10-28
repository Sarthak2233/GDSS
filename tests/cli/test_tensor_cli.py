"""CLI gdss tensor over fixture repos."""

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
        f.write(
            "def add(a, b):\n    return a + b + 1\n\n"
            "def mul(a, b):\n    return a * b\n"
        )
    repo.index.add(["calc.py"])
    repo.index.commit("diverge")
    yield temp_dir, base_name
    shutil.rmtree(temp_dir, ignore_errors=True)


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


def _run_do(shell: GDSSShell, method: str, arg: str = "") -> str:
    buf = StringIO()
    test_console = Console(file=buf, force_terminal=False, width=120)
    with patch("gdss.cli.start.console", test_console):
        getattr(shell, method)(arg)
    return buf.getvalue()


def test_tensor_runs_and_prints_matrix_row(divergent_repo):
    temp_dir, base_name = divergent_repo
    with patch("rich.prompt.Prompt.ask", return_value="default"):
        shell = GDSSShell(temp_dir)
        try:
            out = _run_do(shell, "do_tensor", base_name)
        finally:
            shell.do_quit(None)
    assert "OMEGA" in out.upper() or "Ω" in out or "tensor" in out.lower()
    assert "feature" in out.lower() or base_name.lower() in out.lower()
    assert "R_merge" in out or "merge" in out.lower()


def test_tensor_single_attractor_honest(single_branch_repo):
    temp_dir, branch = single_branch_repo
    with patch("rich.prompt.Prompt.ask", return_value="default"):
        shell = GDSSShell(temp_dir)
        try:
            out = _run_do(shell, "do_tensor", branch)
        finally:
            shell.do_quit(None)
    assert "no other" in out.lower() or "single" in out.lower()


def test_tensor_branch_filtering_cli(divergent_repo):
    temp_dir, base_name = divergent_repo
    with patch("rich.prompt.Prompt.ask", return_value="default"):
        shell = GDSSShell(temp_dir)
        try:
            # Exclude feature: should report no candidates matching filters
            out_exclude = _run_do(shell, "do_tensor", f"{base_name} --exclude feature")
            assert "No candidate" in out_exclude or "matching filters" in out_exclude

            # Include feature: should run and print tensor table
            out_include = _run_do(shell, "do_tensor", f"{base_name} --branches feature")
            assert "feature" in out_include.lower()
        finally:
            shell.do_quit(None)


def test_shell_config_branches_and_hierarchy(divergent_repo):
    temp_dir, base_name = divergent_repo
    with patch("rich.prompt.Prompt.ask", return_value="default"):
        shell = GDSSShell(temp_dir)
        try:
            # Test config branches include
            out_inc = _run_do(shell, "do_config", "branches include feature/*")
            assert "include filters set" in out_inc.lower()

            # Test config branches exclude
            out_exc = _run_do(shell, "do_config", "branches exclude spike/*")
            assert "exclude filters set" in out_exc.lower()

            # Test config hierarchy
            out_hier = _run_do(shell, "do_config", "hierarchy develop staging main")
            assert "priority chain set" in out_hier.lower()

            # Test do_hierarchy command
            out_h_cmd = _run_do(shell, "do_hierarchy")
            assert "PRIORITY CHAIN" in out_h_cmd
            assert "develop" in out_h_cmd
            assert "Active Branch Selection Filters" in out_h_cmd
        finally:
            shell.do_quit(None)
