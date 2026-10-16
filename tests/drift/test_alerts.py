"""DriftAlerts: severity buckets and roadmap-format messages."""

from gdss.drift.alerts import DriftAlerts
from gdss.drift.types import AffectedSymbol, DriftMagnitude, DriftSnapshot


def _snapshot(magnitude: float, affected: tuple[AffectedSymbol, ...] = ()) -> DriftSnapshot:
    return DriftSnapshot(
        branch="feature-auth",
        reference_branch="dev",
        timestamp=1.0,
        magnitude=DriftMagnitude(
            tip_distance=magnitude,
            trajectory_integral=0.0,
            magnitude=magnitude,
            alpha=1.0,
            beta=0.0,
        ),
        velocity=0.0,
        convergence=max(0.0, 1.0 - magnitude),
        affected=affected,
    )


def test_no_alert_below_low_threshold():
    alerts = DriftAlerts()
    assert alerts.evaluate(_snapshot(0.1)) is None


def test_severity_buckets():
    alerts = DriftAlerts(thresholds={"low": 0.25, "medium": 0.5, "high": 0.75})
    low = alerts.evaluate(_snapshot(0.3))
    med = alerts.evaluate(_snapshot(0.6))
    high = alerts.evaluate(_snapshot(0.8))
    assert low is not None and low.severity == "low"
    assert med is not None and med.severity == "medium"
    assert high is not None and high.severity == "high"


def test_message_contains_branch_and_affected_symbol():
    affected = (
        AffectedSymbol(
            symbol_id="auth.py::verify_token",
            name="verify_token",
            distance=0.73,
            reason="modified_in_both",
        ),
    )
    alerts = DriftAlerts()
    alert = alerts.evaluate(_snapshot(0.8, affected=affected))
    assert alert is not None
    text = alerts.format(alert)
    assert "feature-auth" in text
    assert "verify_token" in text
    assert "HIGH DRIFT" in text.upper() or "high" in alert.severity
