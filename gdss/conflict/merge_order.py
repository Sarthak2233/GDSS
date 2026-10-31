"""Greedy merge ordering over pairwise Omega costs."""

from __future__ import annotations

from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass

from gdss.logger import get_logger

logger = get_logger("gdss.conflict.merge_order")


@dataclass(frozen=True)
class MergeOrderStep:
    """One greedy transition in a proposed merge order."""

    source: Hashable
    target: Hashable
    omega: float


@dataclass(frozen=True)
class MergeOrderPlan:
    """A bounded heuristic order, never a proof of globally optimal merging."""

    order: tuple[Hashable, ...]
    baseline_cost: float
    proposed_cost: float
    steps: tuple[MergeOrderStep, ...]
    heuristic: str = "greedy_nearest_neighbor"


def _edge_cost(
    source: Hashable, target: Hashable, costs: Mapping[tuple[Hashable, Hashable], float]
) -> float:
    return float(costs.get((source, target), costs.get((target, source), 1.0)))


def _sequence_cost(
    order: Sequence[Hashable], costs: Mapping[tuple[Hashable, Hashable], float]
) -> float:
    return sum(
        _edge_cost(source, target, costs) for source, target in zip(order, order[1:], strict=False)
    )


def plan_merge_order(
    operators: Sequence[Hashable],
    costs: Mapping[tuple[Hashable, Hashable], float],
    *,
    seed: Hashable | None = None,
) -> MergeOrderPlan:
    """Build a deterministic O(n^2) greedy merge-order heuristic.

    The search is deliberately bounded to local branch/operator counts. It reports
    a path with lower observed pairwise cost when one exists; it does not claim a
    global geodesic optimum.
    """
    indexed = list(enumerate(operators))
    if not indexed:
        return MergeOrderPlan((), 0.0, 0.0, ())

    if seed is None:
        seed_index, seed_operator = min(
            indexed,
            key=lambda item: (
                sum(
                    _edge_cost(item[1], other, costs)
                    for other_index, other in indexed
                    if other_index != item[0]
                ),
                str(item[1]),
                item[0],
            ),
        )
    else:
        seed_index, seed_operator = next((item for item in indexed if item[1] == seed), indexed[0])

    remaining = [item for item in indexed if item[0] != seed_index]
    order: list[Hashable] = [seed_operator]
    steps: list[MergeOrderStep] = []
    while remaining:
        current = order[-1]
        next_index, next_operator = min(
            remaining,
            key=lambda item: (_edge_cost(current, item[1], costs), str(item[1]), item[0]),
        )
        edge = _edge_cost(current, next_operator, costs)
        steps.append(MergeOrderStep(current, next_operator, edge))
        order.append(next_operator)
        remaining = [item for item in remaining if item[0] != next_index]

    plan = MergeOrderPlan(
        order=tuple(order),
        baseline_cost=_sequence_cost(operators, costs),
        proposed_cost=_sequence_cost(order, costs),
        steps=tuple(steps),
    )
    logger.info(
        "Planned merge order for %d branches: %s (baseline cost: %.2f, proposed cost: %.2f)",
        len(operators),
        [str(x) for x in plan.order],
        plan.baseline_cost,
        plan.proposed_cost,
    )
    return plan


def minimize_omega_sequence(
    operators: Sequence[Hashable], costs: Mapping[tuple[Hashable, Hashable], float]
) -> list[Hashable]:
    """Return the legacy list form while retaining the caller's first seed."""
    if not operators:
        return []
    return list(plan_merge_order(operators, costs, seed=operators[0]).order)
