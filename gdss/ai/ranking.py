"""Deterministic ranking of flat conflict-tensor evidence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from gdss.conflict.tensor import ConflictTensor, TensorEntry


@dataclass(frozen=True)
class RankedConflict:
    """A tensor entry with a bounded deterministic confidence score."""

    entry: TensorEntry
    confidence: float
    factors: Mapping[str, float] = field(default_factory=dict)


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, value))


def rank_tensor_entries(
    tensor: ConflictTensor,
    *,
    drift_magnitudes: Mapping[str, float] | None = None,
    anchor_confidence: Mapping[tuple[str, str], float] | None = None,
) -> list[RankedConflict]:
    """Rank sparse tensor entries in O(E log E) with inspectable score factors."""
    entries = list(tensor.entries.values())
    omega_scale = max((entry.omega for entry in entries), default=0.0)
    drift_magnitudes = drift_magnitudes or {}
    drift_scale = max((float(value) for value in drift_magnitudes.values()), default=0.0)
    anchor_confidence = anchor_confidence or {}

    ranked: list[RankedConflict] = []
    for entry in entries:
        omega = entry.omega / omega_scale if omega_scale else 0.0
        branch_drift = (
            float(drift_magnitudes.get(entry.i, 0.0))
            + float(drift_magnitudes.get(entry.j, 0.0))
        ) / 2.0
        drift = _bounded(branch_drift / drift_scale) if drift_scale else 0.0
        interference = float(
            any(reason.startswith("interference=") for reason in entry.reasons)
        )
        dependency = float("dependency_overlap" in entry.reasons)
        anchor = _bounded(
            float(
                anchor_confidence.get(
                    (entry.i, entry.j),
                    anchor_confidence.get((entry.j, entry.i), 1.0),
                )
            )
        )
        factors = {
            "omega": omega,
            "drift": drift,
            "interference": interference,
            "dependency": dependency,
            "anchor": anchor,
        }
        confidence = _bounded(
            0.55 * omega
            + 0.20 * drift
            + 0.15 * interference
            + 0.05 * dependency
            + 0.05 * anchor
        )
        ranked.append(RankedConflict(entry=entry, confidence=confidence, factors=factors))

    return sorted(
        ranked,
        key=lambda candidate: (
            -candidate.confidence,
            -candidate.entry.omega,
            candidate.entry.i,
            candidate.entry.j,
        ),
    )
