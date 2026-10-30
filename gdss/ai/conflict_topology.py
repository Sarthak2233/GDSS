"""Deterministic conflict-topology classification for assistive suggestions."""

from __future__ import annotations

from typing import Literal

from gdss.ai.types import ConflictTopology
from gdss.conflict.commutativity import CommutativityClass, classify
from gdss.core.transform_types import SemanticOperator

SymbolOverlap = Literal[
    "same_symbol",
    "partial",
    "same_parent_disjoint_children",
    "order_sensitive",
    "none",
]


def _operator_names(operator: SemanticOperator) -> set[str]:
    return {
        name
        for name in (
            operator.name,
            operator.from_name,
            operator.to_name,
            operator.get_target_name(),
        )
        if name
    }


def _operator_symbol_ids(operator: SemanticOperator) -> set[str]:
    return {
        symbol_id
        for symbol_id in (
            operator.symbol_id,
            operator.from_symbol_id,
            operator.to_symbol_id,
        )
        if symbol_id
    }


def derive_symbol_overlap(
    operator_i: SemanticOperator, operator_j: SemanticOperator
) -> SymbolOverlap:
    """Infer overlap from operator identities and extractor-produced block evidence."""
    if operator_i.details.get("order_sensitive") or operator_j.details.get("order_sensitive"):
        return "order_sensitive"

    same_symbol = bool(
        _operator_symbol_ids(operator_i) & _operator_symbol_ids(operator_j)
        or _operator_names(operator_i) & _operator_names(operator_j)
    )
    if same_symbol:
        blocks_i = set(operator_i.details.get("changed_blocks", ()))
        blocks_j = set(operator_j.details.get("changed_blocks", ()))
        if blocks_i and blocks_j and (blocks_i & blocks_j):
            return "partial"
        return "same_symbol"

    parent_i = operator_i.details.get("parent_class")
    parent_j = operator_j.details.get("parent_class")
    if parent_i and parent_i == parent_j:
        return "same_parent_disjoint_children"
    return "none"


def classify_conflict(
    operator_i: SemanticOperator,
    operator_j: SemanticOperator,
    *,
    symbol_overlap: SymbolOverlap | None,
    symbol_id: str,
) -> ConflictTopology:
    """Classify a contacting operator pair without producing or applying a patch."""
    commutativity = classify(operator_i, operator_j)
    inferred_overlap = derive_symbol_overlap(operator_i, operator_j)
    overlap = (
        inferred_overlap
        if inferred_overlap in {"same_symbol", "partial", "order_sensitive"}
        else symbol_overlap or inferred_overlap
    )

    kind: Literal["union", "intersection", "disjoint", "asymmetric"]
    if overlap == "same_parent_disjoint_children":
        if commutativity == CommutativityClass.INTERFERE:
            kind = "disjoint"
            verdict = commutativity.value
            justification = "disjoint-child hint conflicts with operator interference"
        else:
            kind = "union"
            verdict = CommutativityClass.COMMUTE.value
            justification = "operators affect disjoint child symbols under one parent"
    elif overlap == "partial":
        kind = "intersection"
        verdict = commutativity.value
        justification = "operators overlap part of the same symbol"
    elif overlap == "order_sensitive":
        kind = "asymmetric"
        verdict = CommutativityClass.INTERFERE.value
        justification = "operator order changes the resulting symbol state"
    elif commutativity == CommutativityClass.INTERFERE:
        kind = "disjoint"
        verdict = commutativity.value
        justification = "operators interfere without a common sub-operator"
    else:
        kind = "union"
        verdict = commutativity.value
        justification = "operators can be retained without semantic interference"

    return ConflictTopology(
        kind=kind,
        symbol_id=symbol_id,
        operator_i=operator_i.operator.value,
        operator_j=operator_j.operator.value,
        commutativity=verdict,
        justification=justification,
    )
