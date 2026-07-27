"""Daemon drift monitor: emit drift events on scan."""

import os
import shutil
import tempfile

import git
import pytest

from gdss.core.ast_parser import ASTParser
from gdss.core.transform_extractor import TransformExtractor
from gdss.drift.engine import DriftEngine
from gdss.drift.history import SnapshotHistory
from gdss.drift.monitor import DriftMonitor
from gdss.runtime.daemon import GDSSDaemon
from gdss.runtime.event_bus import EventBus
from gdss.runtime.registry import RepositoryRegistry
from gdss.storage.db import RuntimeDB
from gdss.watcher.git_observer import GitObserver
from pathlib import Path


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
        f.write("def add(a, b):\n    return a + b + 1\n")
    repo.index.add(["calc.py"])
    repo.index.commit("diverge")
    yield temp_dir, base_name
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_drift_monitor_scan_once_emits_drift_event(divergent_repo):
    temp_dir, base_name = divergent_repo
    bus = EventBus()
    events: list[dict] = []
    bus.subscribe("drift", lambda data: events.append(data))

    observer = GitObserver(temp_dir)
    parser = ASTParser()
    extractor = TransformExtractor()
    engine = DriftEngine(
        observer,
        parser,
        extractor,
        history=SnapshotHistory(Path(temp_dir) / "hist.json"),
    )
    monitor = DriftMonitor(observer, parser, extractor, bus, engine=engine)
    emitted = monitor.scan_once(base_name)

    assert len(emitted) >= 1
    assert any(e.get("event") == "snapshot" for e in events)
    assert any(e.get("branch") == "feature" for e in events)


def test_daemon_loop_invokes_drift_monitor(divergent_repo, tmp_path):
    temp_dir, base_name = divergent_repo
    db = RuntimeDB(str(tmp_path / "runtime.db"))
    registry = RepositoryRegistry(db)
    daemon = GDSSDaemon(temp_dir, registry, db, drift_every=1)
    daemon.context_engine.set_reference_branch(base_name)

    events: list[dict] = []
    daemon.bus.subscribe("drift", lambda data: events.append(data))

    # One synchronous scan (avoid sleeping in the real loop)
    daemon.drift_monitor.scan_once(base_name)
    assert any(e.get("event") == "snapshot" for e in events)
