"""Operator commutativity: type table + pairwise classify (Layer 7).

Does NOT import gdss.drift. Deterministic brain only.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from enum import Enum

from gdss.core.transform_types import OperatorType, SemanticOperator


class CommutativityClass(str, Enum):
    """Outcome of [T_i, T_j] on contacting operators."""

    COMMUTE = "commute"
    INTERFERE = "interfere"
    INDEPENDENT = "independent"


_RENAME = {
    OperatorType.RENAME_FUNCTION,
    OperatorType.RENAME_CLASS,
    OperatorType.RENAME_FILE,
}
_DELETE = {
    OperatorType.DELETE_FUNCTION,
    OperatorType.DELETE_CLASS,
    OperatorType.DELETE_FILE,
    OperatorType.REMOVE_IMPORT,
    OperatorType.REMOVE_DEPENDENCY,
}
_MODIFY = {
    OperatorType.MODIFY_FUNCTION,
    OperatorType.MODIFY_CLASS,
    OperatorType.MODIFY_DEPENDENCY,
    OperatorType.MODIFY_VARIABLE,
    OperatorType.MODIFY_CONSTANT,
}
_ADD = {
    OperatorType.ADD_FUNCTION,
    OperatorType.ADD_CLASS,
    OperatorType.ADD_FILE,
    OperatorType.ADD_IMPORT,
    OperatorType.ADD_DEPENDENCY,
}


def _type_pair_class(a: OperatorType, b: OperatorType) -> CommutativityClass:
    """Classify two operator *types* assuming same-symbol contact."""
    if a in _RENAME and b in _DELETE:
        return CommutativityClass.INTERFERE
    if b in _RENAME and a in _DELETE:
        return CommutativityClass.INTERFERE
    if a in _RENAME and b in _RENAME:
        return CommutativityClass.INTERFERE
    if a in _MODIFY and b in _MODIFY:
        return CommutativityClass.COMMUTE
    if a in _ADD and b in _ADD:
        return CommutativityClass.INTERFERE
    if a in _DELETE and b in _DELETE:
        return CommutativityClass.INTERFERE
    if (a in _RENAME and b in _MODIFY) or (b in _RENAME and a in _MODIFY):
        return CommutativityClass.INTERFERE
    if (a in _DELETE and b in _MODIFY) or (b in _DELETE and a in _MODIFY):
        return CommutativityClass.INTERFERE
    if (a in _ADD and b in _MODIFY) or (b in _ADD and a in _MODIFY):
        return CommutativityClass.INTERFERE
    if (a in _ADD and b in _DELETE) or (b in _ADD and a in _DELETE):
        return CommutativityClass.INTERFERE
    if (a in _ADD and b in _RENAME) or (b in _ADD and a in _RENAME):
        return CommutativityClass.INTERFERE
    # Same-type residual (e.g. import pairs already covered) → interfere if identical types
    if a == b:
        return CommutativityClass.INTERFERE
    return CommutativityClass.INTERFERE


def commutativity_table() -> dict[tuple[OperatorType, OperatorType], CommutativityClass]:
    """Static OperatorType × OperatorType table (same-symbol assumption). Symmetric."""
    types = list(OperatorType)
    table: dict[tuple[OperatorType, OperatorType], CommutativityClass] = {}
    for a in types:
        for b in types:  # dsa:ignore — finite enum Cartesian; |OperatorType| is tiny
            table[(a, b)] = _type_pair_class(a, b)
    return table


def _contact_keys(op: SemanticOperator) -> set[str]:
    keys: set[str] = set()
    for value in (op.name, op.from_name, op.to_name):
        if value:
            keys.add(value)
    return keys


def _ops_contact(op_a: SemanticOperator, op_b: SemanticOperator) -> bool:
    """True if operators share a symbol name / rename endpoint or same file for file ops."""
    ka = _contact_keys(op_a)
    kb = _contact_keys(op_b)
    if ka and kb and (ka & kb):
        return True
    # File-level ops without symbol names: same file counts as contact
    if not ka and not kb and op_a.file and op_a.file == op_b.file:
        return True
    return False


_TABLE: dict[tuple[OperatorType, OperatorType], CommutativityClass] | None = None


def classify(op_a: SemanticOperator, op_b: SemanticOperator) -> CommutativityClass:
    """Pairwise commutativity on operator instances."""
    global _TABLE
    if not _ops_contact(op_a, op_b):
        return CommutativityClass.INDEPENDENT
    if _TABLE is None:
        _TABLE = commutativity_table()
    return _TABLE[(op_a.operator, op_b.operator)]


def operator_interference(
    branch_ops: Sequence[SemanticOperator],
    other_ops: Sequence[SemanticOperator],
) -> tuple[int, int]:
    """
    Count interfering and contacting pairs across two operator sets.

    Complexity: O(B + R + C) where C is contacts via name index (not full B×R when
    names are sparse). Returns (interfering_pairs, total_contact_pairs).
    """
    by_key: dict[str, list[SemanticOperator]] = defaultdict(list)
    for op in other_ops:
        keys = _contact_keys(op)
        if keys:
            for k in keys:
                by_key[k].append(op)
        else:
            by_key[f"__file__:{op.file}"].append(op)

    interfering = 0
    contacts = 0
    seen: set[tuple[int, int]] = set()  # dsa:ignore — pair tracker; separate from seen_ids
    seen_ids: set[int] = set()  # dsa:ignore — per-op_a candidate dedupe buffer

    for op_a in branch_ops:
        candidates: list[SemanticOperator] = []
        keys = _contact_keys(op_a)
        if keys:
            for k in keys:
                candidates.extend(by_key.get(k, ()))
        else:
            candidates.extend(by_key.get(f"__file__:{op_a.file}", ()))

        # Deduplicate candidate objects for this op_a
        uniq: list[tuple[int, SemanticOperator]] = []
        seen_ids.clear()
        for op_b in candidates:
            oid = id(op_b)
            if oid not in seen_ids:
                seen_ids.add(oid)
                uniq.append((oid, op_b))

        id_a = id(op_a)
        for id_b, op_b in uniq:
            pair_id = (id_a, id_b)
            if pair_id in seen:
                continue
            seen.add(pair_id)
            cls = classify(op_a, op_b)
            if cls == CommutativityClass.INDEPENDENT:
                continue
            contacts += 1
            if cls == CommutativityClass.INTERFERE:
                interfering += 1

    return interfering, contacts
