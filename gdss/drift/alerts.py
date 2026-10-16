"""Drift alert generation from snapshots."""

from __future__ import annotations

from gdss.drift.types import DriftAlert, DriftSnapshot


class DriftAlerts:
    """Map DriftSnapshot magnitude to severity-bucketed notifications."""

    def __init__(
        self,
        thresholds: dict[str, float] | None = None,
    ) -> None:
        self.thresholds = thresholds or {"low": 0.25, "medium": 0.5, "high": 0.75}

    def evaluate(self, snapshot: DriftSnapshot) -> DriftAlert | None:
        mag = snapshot.magnitude.magnitude
        low = self.thresholds.get("low", 0.25)
        medium = self.thresholds.get("medium", 0.5)
        high = self.thresholds.get("high", 0.75)
        if mag < low:
            return None
        if mag >= high:
            severity: str = "high"
        elif mag >= medium:
            severity = "medium"
        else:
            severity = "low"
        message = self._build_message(snapshot, severity)
        return DriftAlert(
            severity=severity,  # type: ignore[arg-type]
            branch=snapshot.branch,
            reference_branch=snapshot.reference_branch,
            magnitude=mag,
            message=message,
            affected=snapshot.affected,
            timestamp=snapshot.timestamp,
        )

    def format(self, alert: DriftAlert) -> str:
        return alert.message

    def _build_message(self, snapshot: DriftSnapshot, severity: str) -> str:
        label = f"{severity.upper()} DRIFT ALERT"
        lines = [
            label,
            "",
            f"{snapshot.branch} diverging from {snapshot.reference_branch}",
            f"Magnitude: {snapshot.magnitude.magnitude:.3f}",
            "",
        ]
        if snapshot.affected:
            lines.append("Affected:")
            for sym in snapshot.affected[:8]:
                lines.append(f"- {sym.name}() [semantic distance: {sym.distance:.2f}]")
            lines.append("")
        return "\n".join(lines)
