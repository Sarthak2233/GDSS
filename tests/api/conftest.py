import os
import shutil
import tempfile

import git
import pytest


@pytest.fixture
def repo_path():
    temp_dir = tempfile.mkdtemp()
    repo = git.Repo.init(temp_dir)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test Author")
        cw.set_value("user", "email", "author@example.com")
    path = os.path.join(temp_dir, "a.py")
    with open(path, "w") as f:
        f.write('"""Secret docstring."""\n\ndef function_1():\n    return 42\n')
    repo.index.add(["a.py"])
    repo.index.commit("Initial commit\n\nDetailed message here.")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def divergent_repo(repo_path):
    repo = git.Repo(repo_path)
    base_name = repo.active_branch.name

    feature = repo.create_head("feature")
    repo.head.reference = feature
    repo.head.reset(index=True, working_tree=True)
    path = os.path.join(repo_path, "a.py")
    with open(path, "w") as f:
        f.write(
            '"""Feature docstring."""\n\ndef function_1():\n    return 24\n\ndef function_2():\n    return "new"\n'
        )
    repo.index.add(["a.py"])
    repo.index.commit("Feature commit")
    return repo_path, base_name
