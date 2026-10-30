"""DriftEngine: tip cosine + trajectory integral magnitude + affected symbols."""

import os
import shutil
import tempfile

import git
import pytest

from gdss.core.ast_parser import ASTParser
from gdss.core.transform_extractor import TransformExtractor
from gdss.drift.engine import DriftEngine
from gdss.drift.types import DriftMagnitude, DriftSnapshot
from gdss.embeddings.encoder import DeterministicBagEncoder
from gdss.watcher.git_observer import GitObserver


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
    repo.index.commit("base")
    base_name = repo.active_branch.name

    feature = repo.create_head("feature")
    repo.head.reference = feature
    repo.head.reset(index=True, working_tree=True)
    with open(path, "w") as f:
        f.write("def add(a, b):\n    return a + b + 1\n\ndef mul(a, b):\n    return a * b\n")
    repo.index.add(["calc.py"])
    repo.index.commit("diverge add and mul")

    yield temp_dir, base_name
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def dual_modify_repo():
    """Both attractor and feature modify the same function after fork."""
    temp_dir = tempfile.mkdtemp()
    repo = git.Repo.init(temp_dir)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test")
        cw.set_value("user", "email", "t@example.com")

    path = os.path.join(temp_dir, "auth.py")
    with open(path, "w") as f:
        f.write("def verify_token(t):\n    return True\n")
    repo.index.add(["auth.py"])
    repo.index.commit("base")
    base_name = repo.active_branch.name

    feature = repo.create_head("feature-auth")
    # Attractor evolves
    with open(path, "w") as f:
        f.write("def verify_token(t):\n    return t == 'ok'\n")
    repo.index.add(["auth.py"])
    repo.index.commit("attractor update")

    # Feature evolves from base
    repo.heads[base_name].checkout()
    feature.checkout()
    # Reset feature to base then diverge
    repo.head.reference = feature
    repo.head.reset("HEAD", index=True, working_tree=True)

    # Re-create properly: base at first commit, attractor and feature diverge
    shutil.rmtree(temp_dir, ignore_errors=True)
    temp_dir = tempfile.mkdtemp()
    repo = git.Repo.init(temp_dir)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test")
        cw.set_value("user", "email", "t@example.com")

    path = os.path.join(temp_dir, "auth.py")
    with open(path, "w") as f:
        f.write("def verify_token(t):\n    return True\n")
    repo.index.add(["auth.py"])
    base = repo.index.commit("base")
    base_name = repo.active_branch.name

    # feature from base
    feature = repo.create_head("feature-auth", base)
    repo.head.reference = feature
    repo.head.reset(index=True, working_tree=True)
    with open(path, "w") as f:
        f.write("def verify_token(t):\n    validate_card()\n    return charge(t)\n")
    repo.index.add(["auth.py"])
    repo.index.commit("feature changes verify")

    # attractor from base
    repo.head.reference = repo.heads[base_name]
    repo.head.reset(index=True, working_tree=True)
    with open(path, "w") as f:
        f.write("def verify_token(t):\n    check_redis()\n    return t.startswith('tok')\n")
    repo.index.add(["auth.py"])
    repo.index.commit("attractor changes verify")

    yield temp_dir, base_name, "feature-auth"
    shutil.rmtree(temp_dir, ignore_errors=True)


def _engine(repo_path: str) -> DriftEngine:
    return DriftEngine(
        observer=GitObserver(repo_path),
        parser=ASTParser(),
        extractor=TransformExtractor(),
        encoder=DeterministicBagEncoder(dim=64),
    )


def test_zero_magnitude_when_branch_equals_attractor(branched_repo):
    temp_dir, base_name = branched_repo
    repo = git.Repo(temp_dir)
    repo.heads[base_name].checkout()
    engine = _engine(temp_dir)
    mag = engine.compute_magnitude(branch=base_name, reference_branch=base_name)
    assert mag.tip_distance == pytest.approx(0.0)
    assert mag.trajectory_integral == pytest.approx(0.0)
    assert mag.magnitude == pytest.approx(0.0)


def test_positive_magnitude_for_divergent_branch(branched_repo):
    temp_dir, base_name = branched_repo
    engine = _engine(temp_dir)
    mag = engine.compute_magnitude(branch="feature", reference_branch=base_name)
    assert mag.magnitude > 0.0
    assert mag.tip_distance >= 0.0
    assert mag.trajectory_integral >= 0.0


def test_trajectory_integral_zero_when_no_commits_on_path(branched_repo):
    temp_dir, base_name = branched_repo
    repo = git.Repo(temp_dir)
    repo.heads[base_name].checkout()
    engine = _engine(temp_dir)
    mag = engine.compute_magnitude(branch=base_name, reference_branch=base_name)
    assert mag.trajectory_integral == pytest.approx(0.0)


def test_snapshot_velocity_zero_on_first_then_positive(branched_repo):
    temp_dir, base_name = branched_repo
    from pathlib import Path

    from gdss.drift.history import SnapshotHistory

    hist = SnapshotHistory(Path(temp_dir) / ".gdss" / "drift" / "snapshots.json")
    engine = DriftEngine(
        observer=GitObserver(temp_dir),
        parser=ASTParser(),
        extractor=TransformExtractor(),
        encoder=DeterministicBagEncoder(dim=64),
        history=hist,
    )
    first = engine.snapshot(branch="feature", reference_branch=base_name)
    assert first.velocity == pytest.approx(0.0)
    assert 0.0 <= first.convergence <= 1.0

    # Force a prior lower magnitude by recording an artificial earlier point
    hist.record(
        DriftSnapshot(
            branch="feature",
            reference_branch=base_name,
            timestamp=first.timestamp - 10.0,
            magnitude=DriftMagnitude(0.0, 0.0, 0.0, 0.5, 0.5),
            velocity=0.0,
            convergence=1.0,
            affected=(),
        )
    )
    # Rebuild engine reading same history; compute_magnitude still returns positive
    # so velocity vs the artificial zero should be positive after we order recent correctly.
    # recent takes last n — the artificial record is last, so next snapshot uses mag=0 as prior.
    second = engine.snapshot(branch="feature", reference_branch=base_name)
    assert second.velocity > 0.0
    assert 0.0 <= second.convergence <= 1.0


def test_snapshot_convergence_in_unit_interval(branched_repo):
    temp_dir, base_name = branched_repo
    from pathlib import Path

    from gdss.drift.history import SnapshotHistory

    engine = DriftEngine(
        observer=GitObserver(temp_dir),
        parser=ASTParser(),
        extractor=TransformExtractor(),
        encoder=DeterministicBagEncoder(dim=64),
        history=SnapshotHistory(Path(temp_dir) / "hist.json"),
    )
    snap = engine.snapshot("feature", base_name)
    assert 0.0 <= snap.convergence <= 1.0


def test_affected_symbols_when_both_sides_modify_same_function(dual_modify_repo):
    temp_dir, base_name, feature = dual_modify_repo
    engine = _engine(temp_dir)
    affected = engine.affected_symbols(branch=feature, reference_branch=base_name)
    names = {a.name for a in affected}
    assert "verify_token" in names
    assert all(a.distance >= 0.0 for a in affected)


def test_drift_engine_symbol_and_vector_caching(branched_repo):
    temp_dir, base_name = branched_repo
    from gdss.drift.engine import clear_drift_cache

    clear_drift_cache()
    engine = _engine(temp_dir)
    commit_sha = engine.observer.repo.commit("feature").hexsha

    syms1 = engine._symbols_at_commit(commit_sha)
    syms2 = engine._symbols_at_commit(commit_sha)
    assert syms1 is syms2, "Second call should return cached symbols list"

    vec1 = engine._tip_vector_at(commit_sha, label="feature")
    vec2 = engine._tip_vector_at(commit_sha, label="feature")
    assert vec1 is vec2, "Second call should return cached tip vector"

    clear_drift_cache()
    syms3 = engine._symbols_at_commit(commit_sha)
    assert syms3 is not syms1, "Cache clear should force fresh parse"
