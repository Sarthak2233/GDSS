"""JSON-backed snapshot history for drift velocity."""

from __future__ import annotations

import json
from pathlib import Path

from gdss.drift.types import DriftSnapshot
from gdss.logger import get_logger

logger = get_logger("gdss.drift.history")


class SnapshotHistory:
    """Persist (branch → [(timestamp, magnitude), ...]) under .gdss/drift/."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._data: dict[str, list[list[float]]] = {}
        self._load()

    def record(self, snapshot: DriftSnapshot) -> None:
        row = [float(snapshot.timestamp), float(snapshot.magnitude.magnitude)]
        self._data.setdefault(snapshot.branch, []).append(row)
        self._save()

    def recent(self, branch: str, n: int = 2) -> list[tuple[float, float]]:
        rows = self._data.get(branch, [])
        if n <= 0:
            return []
        selected = rows[-n:]
        return [(float(ts), float(mag)) for ts, mag in selected]

    def _load(self) -> None:
        if not self.path.is_file():
            self._data = {}
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self._data = {
                    str(k): [[float(a), float(b)] for a, b in v]
                    for k, v in raw.items()
                    if isinstance(v, list)
                }
            else:
                self._data = {}
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.debug("Failed reading drift snapshots at %s: %s", self.path, exc)
            self._data = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        logger.debug("Saved drift history to %s", self.path)


def default_history_path(repo_path: str) -> Path:
    return Path(repo_path) / ".gdss" / "drift" / "snapshots.json"
