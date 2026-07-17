from gdss.runtime.context_engine import ContextEngine
from gdss.runtime.event_bus import EventBus
from gdss.runtime.registry import RepositoryRegistry
from gdss.storage.db import RuntimeDB


def test_reference_branch_persists_via_hierarchy(tmp_path):
    db_path = tmp_path / "runtime.db"
    db = RuntimeDB(str(db_path))
    registry = RepositoryRegistry(db)
    repo_id = db.register_repository("test", str(tmp_path))
    bus = EventBus()
    engine = ContextEngine(repo_id, registry, bus)

    assert engine.get_reference_branch() == "main"
    engine.set_reference_branch("develop")
    assert engine.get_reference_branch() == "develop"

    # Reload from DB
    engine2 = ContextEngine(repo_id, registry, bus)
    assert engine2.get_reference_branch() == "develop"
