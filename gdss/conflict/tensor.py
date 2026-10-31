"""Conflict tensor Omega_ij (Layer 7). Does NOT import gdss.drift."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from gdss.conflict.commutativity import operator_interference
from gdss.core.transform_types import OperatorType, SemanticOperator
from gdss.logger import get_logger

logger = get_logger("gdss.conflict.tensor")

_MODIFY_DELETE = {
    OperatorType.MODIFY_FUNCTION,
    OperatorType.MODIFY_CLASS,
    OperatorType.MODIFY_VARIABLE,
    OperatorType.MODIFY_CONSTANT,
    OperatorType.MODIFY_DEPENDENCY,
    OperatorType.DELETE_FUNCTION,
    OperatorType.DELETE_CLASS,
    OperatorType.DELETE_FILE,
    OperatorType.REMOVE_IMPORT,
    OperatorType.REMOVE_DEPENDENCY,
}


@dataclass(frozen=True)
class TensorEntry:
    i: str
    j: str
    omega: float
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ConflictTensor:
    """Sparse Omega matrix. merge_risk = sum of stored entry omegas (each unordered pair once + diagonal)."""

    branches: tuple[str, ...]
    entries: dict[tuple[str, str], TensorEntry]
    merge_risk: float


def _files(ops: Sequence[SemanticOperator]) -> set[str]:
    return {op.file for op in ops if op.file}


def _target_names(ops: Sequence[SemanticOperator]) -> set[str]:
    names: set[str] = set()
    for op in ops:
        name = op.get_target_name()
        if name:
            names.add(name)
        if op.from_name:
            names.add(op.from_name)
        if op.to_name:
            names.add(op.to_name)
    return names


def _mod_del_names(ops: Sequence[SemanticOperator]) -> set[str]:
    names: set[str] = set()
    for op in ops:
        if op.operator not in _MODIFY_DELETE:
            continue
        name = op.get_target_name()
        if name:
            names.add(name)
    return names


_EMPTY_IMPACT: set[str] = set()


class TensorEngine:
    """Deterministic sparse Omega_ij from operator sets + caller-supplied drift magnitudes."""

    def __init__(
        self,
        *,
        w_file: float = 0.2,
        w_function: float = 0.5,
        w_symbol: float = 0.7,
        w_dependency: float = 0.4,
        w_interfere: float = 0.3,
    ) -> None:
        self.w_file = w_file
        self.w_function = w_function
        self.w_symbol = w_symbol
        self.w_dependency = w_dependency
        self.w_interfere = w_interfere

    def compute(
        self,
        branch_ops: Mapping[str, list[SemanticOperator]],
        drift_magnitudes: Mapping[str, float],
        impact_sets: Mapping[str, set[str]] | None = None,
    ) -> ConflictTensor:
        branches = tuple(sorted(branch_ops.keys()))
        logger.debug("Computing conflict tensor Omega for branches: %s", branches)
        entries: dict[tuple[str, str], TensorEntry] = {}
        impact_sets = impact_sets or {}

        # Diagonal self-energy from drift
        for branch in branches:
            mag = float(drift_magnitudes.get(branch, 0.0))
            if mag > 0:
                entries[(branch, branch)] = TensorEntry(
                    i=branch,
                    j=branch,
                    omega=min(1.0, mag),
                    reasons=("drift_self_energy",),
                )

        # Off-diagonal unordered pairs (store lexicographic key once)
        n = len(branches)
        for ai in range(n):
            for aj in range(ai + 1, n):
                i = branches[ai]
                j = branches[aj]
                ops_i = branch_ops[i]
                ops_j = branch_ops[j]

                files_i = _files(ops_i)
                files_j = _files(ops_j)
                same_file = 1.0 if (files_i & files_j) else 0.0

                fn_i = _mod_del_names(ops_i)
                fn_j = _mod_del_names(ops_j)
                same_function = 1.0 if (fn_i & fn_j) else 0.0

                sym_i = _target_names(ops_i)
                sym_j = _target_names(ops_j)
                same_symbol = 1.0 if (sym_i & sym_j) else 0.0

                impact_i = impact_sets.get(i, _EMPTY_IMPACT)
                impact_j = impact_sets.get(j, _EMPTY_IMPACT)
                dep_term = 1.0 if impact_i and impact_j and (impact_i & impact_j) else 0.0

                interfering, contacts = operator_interference(ops_i, ops_j)
                interference = interfering / max(1, contacts) if contacts else 0.0

                omega = (
                    self.w_file * same_file
                    + self.w_function * same_function
                    + self.w_symbol * same_symbol
                    + self.w_dependency * dep_term
                    + self.w_interfere * interference
                )
                omega = max(0.0, min(1.0, omega))

                if omega <= 0:
                    continue

                reasons: list[str] = []
                if same_file:
                    reasons.append("same_file")
                if same_function:
                    reasons.append("same_function")
                if same_symbol:
                    reasons.append("same_symbol")
                if dep_term:
                    reasons.append("dependency_overlap")
                if interference > 0:
                    reasons.append(f"interference={interference:.2f}")

                entries[(i, j)] = TensorEntry(i=i, j=j, omega=omega, reasons=tuple(reasons))

        merge_risk = sum(e.omega for e in entries.values())
        return ConflictTensor(branches=branches, entries=entries, merge_risk=merge_risk)
