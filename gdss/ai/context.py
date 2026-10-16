"""Compatibility re-exports for deterministic branch analysis context.

Canonical implementation lives in ``gdss.drift.context``.
"""

from __future__ import annotations

from gdss.drift.context import (
    AnalysisContext,
    AnalysisContextError,
    build_analysis_context,
    build_pr_analysis_context,
    iter_contact_pairs,
)

__all__ = [
    "AnalysisContext",
    "AnalysisContextError",
    "build_analysis_context",
    "build_pr_analysis_context",
    "iter_contact_pairs",
]
