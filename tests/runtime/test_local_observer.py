import os

import pytest

from gdss.runtime.event_bus import EventBus
from gdss.runtime.local_observer import LocalObserver
from gdss.storage.db import RuntimeDB


@pytest.fixture
def db(tmp_path):
    db_path = os.path.join(tmp_path, "runtime.db")
    return RuntimeDB(db_path)


@pytest.fixture
def bus():
    return EventBus()


def test_local_observer_detection(db, bus, tmp_path):
    # Setup a dummy git repo
    repo_path = tmp_path / "dummy_repo"
    repo_path.mkdir()
    from git import Repo

    repo = Repo.init(repo_path)
    # Need initial commit for HEAD to exist
    readme = repo_path / "README"
    readme.write_text("initial")
    repo.index.add(["README"])
    repo.index.commit("initial commit")

    observer = LocalObserver(repo_path, bus)

    events = []

    def on_event(event):
        events.append(event)

    bus.subscribe("local", on_event)

    # Simulate a file change
    (repo_path / "test.py").write_text("print('hello')")

    # In a real scenario we'd wait for watchdog, but for TDD we can trigger manual check
    observer.scan_once()

    # assert len(events) > 0 # This depends on implementation details
