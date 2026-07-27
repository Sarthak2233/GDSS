"""Drift value types: magnitude, affected symbols, snapshots, alerts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class DriftMagnitude:
    """Combined tip proxy + trajectory integral drift magnitude.

    magnitude = alpha * tip_distance + beta * trajectory_integral
    (trajectory_integral is ceiling-normalized into ~[0, 1]).
    """

    tip_distance: float
    trajectory_integral: float
    magnitude: float
    alpha: float = 0.5
    beta: float = 0.5


@dataclass(frozen=True)
class AffectedSymbol:
    """A symbol contributing to branch/attractor interference."""

    symbol_id: str
    name: str
    distance: float
    reason: str


@dataclass(frozen=True)
class DriftSnapshot:
    """Point-in-time drift measurement for one branch vs its attractor."""

    branch: str
    reference_branch: str
    timestamp: float
    magnitude: DriftMagnitude
    velocity: float
    convergence: float
    affected: tuple[AffectedSymbol, ...]


@dataclass(frozen=True)
class DriftAlert:
    """Severity-bucketed human-readable drift notification."""

    severity: Literal["low", "medium", "high"]
    branch: str
    reference_branch: str
    magnitude: float
    message: str
    affected: tuple[AffectedSymbol, ...]
    timestamp: float
