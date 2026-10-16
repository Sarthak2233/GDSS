"""Background drift monitor: scan local branches and emit drift events."""

from __future__ import annotations

import time

from gdss.core.ast_parser import ASTParser
from gdss.core.transform_extractor import TransformExtractor
from gdss.drift.alerts import DriftAlerts
from gdss.drift.engine import DriftEngine
from gdss.runtime.event_bus import EventBus
from gdss.watcher.git_observer import GitObserver


class DriftMonitor:
    """Iterate local branches, snapshot drift, emit EventBus 'drift' events."""

    def __init__(
        self,
        observer: GitObserver,
        parser: ASTParser,
        extractor: TransformExtractor,
        bus: EventBus,
        engine: DriftEngine | None = None,
        alerts: DriftAlerts | None = None,
    ) -> None:
        self.observer = observer
        self.parser = parser
        self.extractor = extractor
        self.bus = bus
        self.engine = engine or DriftEngine(observer, parser, extractor)
        self.alerts = alerts or DriftAlerts()

    def scan_once(self, reference_branch: str) -> list[dict]:
        """Compute drift for each non-reference branch; emit snapshot (+ alert) events."""
        emitted: list[dict] = []
        if not self.observer.is_valid():
            return emitted

        branches = self.observer.list_local_branches()
        active = self.observer.get_active_branch()
        for branch in branches:
            if branch == reference_branch:
                continue
            try:
                snap = self.engine.snapshot(branch, reference_branch)  # dsa:ignore
            except Exception:
                continue
            payload = {
                "event": "snapshot",
                "branch": snap.branch,
                "reference_branch": snap.reference_branch,
                "magnitude": snap.magnitude.magnitude,
                "tip_distance": snap.magnitude.tip_distance,
                "trajectory_integral": snap.magnitude.trajectory_integral,
                "velocity": snap.velocity,
                "convergence": snap.convergence,
                "active": branch == active,
                "timestamp": snap.timestamp,
                "affected": [
                    {"name": a.name, "distance": a.distance, "symbol_id": a.symbol_id}
                    for a in snap.affected
                ],
            }
            self.bus.emit("drift", payload)
            emitted.append(payload)

            alert = self.alerts.evaluate(snap)
            if alert is not None:
                alert_payload = {
                    "event": "alert",
                    "branch": alert.branch,
                    "reference_branch": alert.reference_branch,
                    "severity": alert.severity,
                    "magnitude": alert.magnitude,
                    "message": alert.message,
                    "timestamp": alert.timestamp,
                }
                self.bus.emit("drift", alert_payload)
                emitted.append(alert_payload)

        # Always emit a heartbeat for the active branch even if it is the attractor
        if active and active == reference_branch and not emitted:
            now = time.time()
            heartbeat = {
                "event": "snapshot",
                "branch": active,
                "reference_branch": reference_branch,
                "magnitude": 0.0,
                "tip_distance": 0.0,
                "trajectory_integral": 0.0,
                "velocity": 0.0,
                "convergence": 1.0,
                "active": True,
                "timestamp": now,
                "affected": [],
            }
            self.bus.emit("drift", heartbeat)
            emitted.append(heartbeat)

        return emitted
