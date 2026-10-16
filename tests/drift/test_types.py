"""Drift value types: construction, immutability, magnitude invariant."""

import pytest

from gdss.drift.types import (
    AffectedSymbol,
    DriftAlert,
    DriftMagnitude,
    DriftSnapshot,
)


def test_drift_magnitude_combined_invariant():
    mag = DriftMagnitude(
        tip_distance=0.4,
        trajectory_integral=0.6,
        magnitude=0.5,
        alpha=0.5,
        beta=0.5,
    )
    expected = mag.alpha * mag.tip_distance + mag.beta * mag.trajectory_integral
    assert mag.magnitude == pytest.approx(expected)


def test_drift_magnitude_is_frozen():
    mag = DriftMagnitude(
        tip_distance=0.1,
        trajectory_integral=0.2,
        magnitude=0.15,
        alpha=0.5,
        beta=0.5,
    )
    with pytest.raises(AttributeError):
        mag.tip_distance = 0.9  # type: ignore[misc]


def test_affected_symbol_and_snapshot_construction():
    affected = AffectedSymbol(
        symbol_id="mod.py::fn",
        name="fn",
        distance=0.73,
        reason="modified_in_both",
    )
    mag = DriftMagnitude(
        tip_distance=0.4,
        trajectory_integral=0.6,
        magnitude=0.5,
        alpha=0.5,
        beta=0.5,
    )
    snap = DriftSnapshot(
        branch="feature-auth",
        reference_branch="dev",
        timestamp=1.0,
        magnitude=mag,
        velocity=0.0,
        convergence=0.5,
        affected=(affected,),
    )
    assert snap.branch == "feature-auth"
    assert len(snap.affected) == 1
    assert snap.affected[0].name == "fn"


def test_drift_alert_severity_literal():
    alert = DriftAlert(
        severity="high",
        branch="feature-auth",
        reference_branch="dev",
        magnitude=0.8,
        message="HIGH DRIFT ALERT",
        affected=(),
        timestamp=1.0,
    )
    assert alert.severity == "high"
