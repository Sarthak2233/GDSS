"""Compatibility re-exports for greedy merge ordering.

Canonical deterministic implementation lives in ``gdss.conflict.merge_order``.
"""

from __future__ import annotations

from gdss.conflict.merge_order import (
    MergeOrderPlan,
    MergeOrderStep,
    minimize_omega_sequence,
    plan_merge_order,
)

__all__ = [
    "MergeOrderPlan",
    "MergeOrderStep",
    "minimize_omega_sequence",
    "plan_merge_order",
]
