"""Assistive AI convergence layer for GDSS.

This layer proposes and validates suggestions; it never applies them.
"""

from gdss.ai.orchestration import (
    ConvergenceState,
    OrchestrationPipeline,
    build_langgraph_workflow,
    run_convergence_pipeline,
)
from gdss.ai.suggester import suggest
from gdss.ai.suggestion_store import (
    is_suggestion_stale,
    list_suggestions,
    load_suggestion,
    save_suggestion,
)

__all__ = [
    "ConvergenceState",
    "OrchestrationPipeline",
    "build_langgraph_workflow",
    "is_suggestion_stale",
    "list_suggestions",
    "load_suggestion",
    "run_convergence_pipeline",
    "save_suggestion",
    "suggest",
]
