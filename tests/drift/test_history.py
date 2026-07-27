"""SnapshotHistory: JSON-backed drift magnitude time series."""

import json
import tempfile
from pathlib import Path

from gdss.drift.history import SnapshotHistory
from gdss.drift.types import DriftMagnitude, DriftSnapshot


def _snap(branch: str, ts: float, mag: float) -> DriftSnapshot:
    return DriftSnapshot(
        branch=branch,
        reference_branch="main",
        timestamp=ts,
        magnitude=DriftMagnitude(
            tip_distance=mag,
            trajectory_integral=0.0,
            magnitude=mag,
            alpha=1.0,
            beta=0.0,
        ),
        velocity=0.0,
        convergence=1.0 - mag,
        affected=(),
    )


def test_record_and_recent_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "snapshots.json"
        hist = SnapshotHistory(path)
        hist.record(_snap("feature", 1.0, 0.1))
        hist.record(_snap("feature", 2.0, 0.3))
        hist.record(_snap("other", 2.5, 0.5))
        recent = hist.recent("feature", n=2)
        assert len(recent) == 2
        assert recent[0] == (1.0, 0.1)
        assert recent[1] == (2.0, 0.3)


def test_recent_empty_for_unknown_branch():
    with tempfile.TemporaryDirectory() as tmp:
        hist = SnapshotHistory(Path(tmp) / "snapshots.json")
        assert hist.recent("missing", n=5) == []


def test_persists_across_instances():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "snapshots.json"
        SnapshotHistory(path).record(_snap("feature", 1.0, 0.2))
        recent = SnapshotHistory(path).recent("feature", n=1)
        assert recent == [(1.0, 0.2)]
        assert path.is_file()
        data = json.loads(path.read_text())
        assert "feature" in data
