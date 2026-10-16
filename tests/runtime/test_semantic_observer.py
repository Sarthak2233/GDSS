import os

import pytest
from git import Repo

from gdss.runtime.event_bus import EventBus
from gdss.runtime.local_observer import LocalObserver


@pytest.fixture
def repo(tmp_path):
    repo_path = tmp_path / "test-repo"
    os.makedirs(repo_path)
    repo = Repo.init(repo_path)

    # Create initial file
    with open(repo_path / "test.py", "w") as f:
        f.write("def foo():\n    return 1")
    repo.index.add(["test.py"])
    repo.index.commit("Initial commit")
    return repo, repo_path

def test_semantic_observer_emits_operators(repo):
    repo_obj, repo_path = repo
    bus = EventBus()
    observer = LocalObserver(str(repo_path), bus)

    captured_events = []
    bus.subscribe("local", lambda data: captured_events.append(data))

    # Modify file: rename function foo -> bar
    with open(repo_path / "test.py", "w") as f:
        f.write("def bar():\n    return 1")
    repo_obj.index.add(["test.py"])
    repo_obj.index.commit("Rename foo to bar")

    # Run scan
    observer.scan_once()

    assert len(captured_events) == 1
    event = captured_events[0]
    assert "semantic_operators" in event
    assert len(event["semantic_operators"]) > 0

    # Find the rename operator
    rename_op = next((op for op in event["semantic_operators"]
                      if op["operator"] == "rename_function"), None)

    assert rename_op is not None
    assert rename_op["from_name"] == "foo"
    assert rename_op["to_name"] == "bar"
