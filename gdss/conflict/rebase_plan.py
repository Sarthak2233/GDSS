"""Discrete semantic rebase planning."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from gdss.conflict.commutativity import CommutativityClass, classify
from gdss.core.transform_types import OperatorType, SemanticOperator
from gdss.logger import get_logger

logger = get_logger("gdss.conflict.rebase_plan")


@dataclass(frozen=True)
class TransportPlan:
    """Read-only semantic rebase result with explicit operator dispositions."""

    kept: tuple[SemanticOperator, ...]
    already_applied: tuple[SemanticOperator, ...]
    blocked: tuple[SemanticOperator, ...]
    file_remaps: Mapping[str, str]


def _semantic_key(operator: SemanticOperator) -> tuple[str, ...]:
    """Identity independent of timestamp, author, commit, and display metadata."""
    return (
        operator.operator.value,
        operator.file,
        operator.symbol_id or "",
        operator.from_symbol_id or "",
        operator.to_symbol_id or "",
        operator.name or "",
        operator.from_name or "",
        operator.to_name or "",
    )


def _contact_keys(operator: SemanticOperator) -> tuple[str, ...]:
    names = tuple(name for name in (operator.name, operator.from_name, operator.to_name) if name)
    if names:
        return tuple(f"{operator.file}\x1f{name}" for name in names)
    return (f"{operator.file}\x1f<file>",)


def _file_remaps(frame: Sequence[SemanticOperator]) -> dict[str, str]:
    return {
        operator.from_name: operator.to_name
        for operator in frame
        if (
            operator.operator == OperatorType.RENAME_FILE
            and operator.from_name
            and operator.to_name
        )
    }


def _remap_operator(operator: SemanticOperator, file_remaps: Mapping[str, str]) -> SemanticOperator:
    remapped_file = file_remaps.get(operator.file, operator.file)
    return replace(operator, file=remapped_file)


def build_transport_plan(
    operators_j: Sequence[SemanticOperator], frame_i: Sequence[SemanticOperator]
) -> TransportPlan:
    """Transport branch-j operators in O(j+i+c) indexed contact time.

    ``c`` is the number of same-file-and-symbol contacts. The plan is intentionally
    read-only: it reports blocked operations instead of applying a rebase.
    """
    file_remaps = _file_remaps(frame_i)
    exact: dict[tuple[str, ...], list[SemanticOperator]] = defaultdict(list)
    contacts: dict[str, list[SemanticOperator]] = defaultdict(list)  # dsa:ignore
    for existing in frame_i:
        exact[_semantic_key(existing)].append(existing)
        for key in _contact_keys(existing):
            contacts[key].append(existing)

    kept: list[SemanticOperator] = []
    already_applied: list[SemanticOperator] = []
    blocked: list[SemanticOperator] = []
    for original in operators_j:
        candidate = _remap_operator(original, file_remaps)
        equivalents = exact.get(_semantic_key(candidate), ())
        if any(
            classify(candidate, existing) == CommutativityClass.COMMUTE for existing in equivalents
        ):
            already_applied.append(original)
            continue

        seen: set[int] = set()
        interfering = False
        for key in _contact_keys(candidate):
            for existing in contacts.get(key, ()):
                identifier = id(existing)
                if identifier in seen:
                    continue
                seen.add(identifier)
                if classify(candidate, existing) == CommutativityClass.INTERFERE:  # dsa:ignore
                    interfering = True
                    break
            if interfering:
                break
        if interfering:
            blocked.append(candidate)
        else:
            kept.append(candidate)

    plan = TransportPlan(
        kept=tuple(kept),
        already_applied=tuple(already_applied),
        blocked=tuple(blocked),
        file_remaps=dict(file_remaps),
    )
    logger.debug(
        "Semantic rebase transport plan: %d kept, %d already applied, %d blocked",
        len(plan.kept),
        len(plan.already_applied),
        len(plan.blocked),
    )
    return plan


def parallel_transport(
    operators_j: Sequence[SemanticOperator], frame_i: Sequence[SemanticOperator]
) -> list[SemanticOperator]:
    """Backward-compatible shorthand for the transport plan's applicable operators."""
    return list(build_transport_plan(operators_j, frame_i).kept)
