"""Heuristic conflict probability estimator (Layer 7).

Does NOT import gdss.drift — callers pass drift_magnitude as a float input.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from gdss.core.transform_types import OperatorType, SemanticOperator

_INTERFERING = {
    OperatorType.RENAME_FUNCTION,
    OperatorType.RENAME_CLASS,
    OperatorType.DELETE_FUNCTION,
    OperatorType.DELETE_CLASS,
    OperatorType.MODIFY_FUNCTION,
    OperatorType.MODIFY_CLASS,
}

_RENAME_OPS = {OperatorType.RENAME_FUNCTION, OperatorType.RENAME_CLASS}
_TOUCH_OPS = {
    OperatorType.DELETE_FUNCTION,
    OperatorType.DELETE_CLASS,
    OperatorType.MODIFY_FUNCTION,
    OperatorType.MODIFY_CLASS,
}


@dataclass(frozen=True)
class ConflictProbability:
    """Heuristic conflict risk in [0, 1] with human-readable reasons."""

    score: float
    reasons: tuple[str, ...]


def _target_names(ops: Sequence[SemanticOperator]) -> set[str]:
    names: set[str] = set()
    for op in ops:
        name = op.get_target_name()
        if name:
            names.add(name)
    return names


class ConflictProbabilityEstimator:
    """Weighted heuristic over shared files, symbol overlap, ops, and drift."""

    def __init__(
        self,
        w_shared_files: float = 0.25,
        w_symbol_overlap: float = 0.25,
        w_interference: float = 0.25,
        w_drift: float = 0.25,
    ) -> None:
        self.w_shared_files = w_shared_files
        self.w_symbol_overlap = w_symbol_overlap
        self.w_interference = w_interference
        self.w_drift = w_drift

    def estimate(
        self,
        branch_ops: Sequence[SemanticOperator],
        reference_ops: Sequence[SemanticOperator],
        shared_files: Sequence[str],
        drift_magnitude: float,
    ) -> ConflictProbability:
        reasons: list[str] = []
        parts: list[float] = []

        shared = list(shared_files)
        if shared:
            file_score = min(1.0, len(shared) / 3.0)
            parts.append(self.w_shared_files * file_score)
            reasons.append(f"shared modified files: {', '.join(shared[:5])}")

        branch_names = _target_names(branch_ops)
        ref_names = _target_names(reference_ops)
        overlap = branch_names & ref_names
        if overlap:
            overlap_score = min(1.0, len(overlap) / 3.0)
            parts.append(self.w_symbol_overlap * overlap_score)
            reasons.append(f"symbol overlap: {', '.join(sorted(overlap)[:5])}")

        interference = self._operator_interference(branch_ops, reference_ops)
        if interference > 0:
            parts.append(self.w_interference * interference)
            reasons.append("operator interference (rename/modify/delete collision)")

        drift = max(0.0, min(1.0, float(drift_magnitude)))
        if drift > 0:
            parts.append(self.w_drift * drift)
            reasons.append(f"drift magnitude: {drift:.3f}")

        if not parts:
            return ConflictProbability(score=0.0, reasons=())

        score = min(1.0, sum(parts))
        return ConflictProbability(score=float(score), reasons=tuple(reasons))

    @staticmethod
    def _operator_interference(
        branch_ops: Sequence[SemanticOperator],
        reference_ops: Sequence[SemanticOperator],
    ) -> float:
        """Detect rename/modify/delete collisions on the same symbol name."""
        branch_by_name: dict[str, set[OperatorType]] = {}
        for op in branch_ops:
            name = op.get_target_name()  # dsa:ignore
            if not name or op.operator not in _INTERFERING:
                continue
            names = {name}
            if op.from_name:
                names.add(op.from_name)
            if op.to_name:
                names.add(op.to_name)
            for n in names:
                if n not in branch_by_name:
                    branch_by_name[n] = set()  # dsa:ignore
                branch_by_name[n].add(op.operator)

        hits = 0
        checked = 0
        for op in reference_ops:
            name = op.get_target_name()  # dsa:ignore
            if not name or op.operator not in _INTERFERING:
                continue
            names = {name}
            if op.from_name:
                names.add(op.from_name)
            if op.to_name:
                names.add(op.to_name)
            for n in names:
                if n in branch_by_name:
                    checked += 1
                    if branch_by_name[n]:
                        hits += 1
                        break
        if checked == 0 and hits == 0:
            branch_from = {
                op.from_name
                for op in branch_ops
                if op.operator in _RENAME_OPS and op.from_name
            }
            ref_targets: set[str] = set()
            for op in reference_ops:
                if op.operator not in _TOUCH_OPS:
                    continue
                name = op.get_target_name()  # dsa:ignore
                if name:
                    ref_targets.add(name)
            if branch_from & ref_targets:
                return 1.0
            return 0.0
        return min(1.0, hits / max(checked, 1))
