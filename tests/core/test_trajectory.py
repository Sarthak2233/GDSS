import os
import tempfile
import shutil
import git
import pytest

from gdss.core.ast_parser import ASTParser
from gdss.core.transform_extractor import TransformExtractor
from gdss.core.transform_types import OperatorType
from gdss.watcher.git_observer import GitObserver
from gdss.core.trajectory import extract_trajectory_operators


@pytest.fixture
def branched_repo():
    temp_dir = tempfile.mkdtemp()
    repo = git.Repo.init(temp_dir)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test")
        cw.set_value("user", "email", "t@example.com")

    path = os.path.join(temp_dir, "calc.py")
    with open(path, "w") as f:
        f.write("def add(a, b):\n    return a + b\n")
    repo.index.add(["calc.py"])
    base = repo.index.commit("base")
    # Ensure a named base branch tip
    base_name = repo.active_branch.name

    feature = repo.create_head("feature")
    repo.head.reference = feature
    repo.head.reset(index=True, working_tree=True)
    with open(path, "w") as f:
        f.write(
            "def add(a, b):\n    return a + b\n\n"
            "def mul(a, b):\n    return a * b\n"
        )
    repo.index.add(["calc.py"])
    repo.index.commit("add mul")

    yield temp_dir, base_name
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_trajectory_operators_from_merge_base_to_head(branched_repo):
    temp_dir, base_name = branched_repo
    observer = GitObserver(temp_dir)
    ops = extract_trajectory_operators(
        observer,
        ASTParser(),
        TransformExtractor(),
        ref_branch=base_name,
        head="HEAD",
    )
    adds = [op for op in ops if op.operator == OperatorType.ADD_FUNCTION]
    assert any(op.name == "mul" for op in adds)


def test_trajectory_empty_when_on_attractor(branched_repo):
    temp_dir, base_name = branched_repo
    repo = git.Repo(temp_dir)
    repo.heads[base_name].checkout()
    observer = GitObserver(temp_dir)
    ops = extract_trajectory_operators(
        observer,
        ASTParser(),
        TransformExtractor(),
        ref_branch=base_name,
        head="HEAD",
    )
    assert ops == []
