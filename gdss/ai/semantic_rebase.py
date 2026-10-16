"""Compatibility re-exports for discrete semantic rebase planning.

Canonical deterministic implementation lives in ``gdss.conflict.rebase_plan``.
"""

from __future__ import annotations

from gdss.conflict.rebase_plan import (
    TransportPlan,
    build_transport_plan,
    parallel_transport,
)

__all__ = [
    "TransportPlan",
    "build_transport_plan",
    "parallel_transport",
]
