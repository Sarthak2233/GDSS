"""Tests for gdss.ai.orchestration (Phase 5a Agent Orchestration)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from gdss.ai.orchestration import (
    ConvergenceState,
    OrchestrationPipeline,
    build_langgraph_workflow,
)
from gdss.ai.suggestion_store import list_suggestions


def test_convergence_state_initialization():
    state = ConvergenceState(
        repo_path=".",
        reference_branch="main",
    )
    assert state.checkpoint == "init"
    assert state.suggestions == []
    assert state.errors == []
    assert state.llm is False
    assert state.validate is False


def test_orchestration_pipeline_model_free(tmp_path: Path, monkeypatch):
    # Setup mock suggestions from suggest()
    from gdss.ai.types import Suggestion, SuggestionAnchor, SuggestionContext

    anchor = SuggestionAnchor(
        file_path="app.py",
        line_start=1,
        line_end=5,
    )
    context = SuggestionContext(
        reference_branch="main",
        candidate_branch="feature",
        omega=0.5,
        merge_risk=0.2,
        operator_i_id="i",
        operator_j_id="j",
    )
    mock_sug = Suggestion(
        kind="conflict",
        file_path="app.py",
        line_start=1,
        line_end=5,
        symbol_id="app.py::foo",
        operator="modify_function",
        action="review",
        rationale="conflict",
        reason=("collision",),
        confidence=0.9,
        anchor=anchor,
        context=context,
    )

    def mock_suggest(*args, **kwargs):
        return [mock_sug]

    monkeypatch.setattr("gdss.ai.orchestration.suggest", mock_suggest)

    pipeline = OrchestrationPipeline(
        repo_path=str(tmp_path),
        reference_branch="main",
        target_commit="commit_abc123",
        llm=False,
        validate=False,
    )

    final_state = pipeline.run()

    # Invariants check
    assert final_state.checkpoint == "awaiting_human_review"
    assert len(final_state.suggestions) == 1
    assert final_state.suggestions[0].suggestion_id != ""

    # Audited suggestion state must be saved to .gdss/suggestions/
    saved = list_suggestions(tmp_path)
    assert len(saved) == 1
    assert saved[0]["id"] == final_state.suggestions[0].suggestion_id
    assert saved[0]["target_commit"] == "commit_abc123"


def test_orchestration_pipeline_with_validation(tmp_path: Path, monkeypatch):
    from gdss.ai.types import PatchCombination, Suggestion, SuggestionAnchor, SuggestionContext

    anchor = SuggestionAnchor(
        file_path="calc.py",
        line_start=10,
        line_end=20,
    )
    context = SuggestionContext(
        reference_branch="main",
        candidate_branch="feature",
        omega=0.6,
        merge_risk=0.3,
        operator_i_id="i",
        operator_j_id="j",
    )
    combo = PatchCombination(
        label="take_left",
        strategy="keep left",
        patch_text="--- a/calc.py\n+++ b/calc.py\n+def add(a, b): return a + b\n",
    )
    mock_sug = Suggestion(
        kind="conflict",
        file_path="calc.py",
        line_start=10,
        line_end=20,
        symbol_id="calc.py::add",
        operator="modify_function",
        action="review",
        rationale="conflict",
        reason=("collision",),
        confidence=0.9,
        anchor=anchor,
        context=context,
        patch_combinations=[combo],
    )

    monkeypatch.setattr("gdss.ai.orchestration.suggest", lambda *args, **kwargs: [mock_sug])

    # 1. Test injected validator callable
    mock_validator = MagicMock(return_value=(True, None))

    pipeline = OrchestrationPipeline(
        repo_path=str(tmp_path),
        reference_branch="main",
        target_commit="commit_def456",
        llm=False,
        validate=True,
        validator=mock_validator,
    )

    final_state = pipeline.run()
    assert final_state.checkpoint == "awaiting_human_review"
    sug = final_state.suggestions[0]
    assert sug.patch_combinations[0].validated is True
    assert sug.patch_combinations[0].validation_status == "validated"
    mock_validator.assert_called_once()

    # 2. Test dynamic sandbox resolution
    mock_sandbox = MagicMock()
    mock_sandbox.validate_patch.return_value = MagicMock(is_clean=True, error_summary=None)
    monkeypatch.setattr("gdss.validation.sandbox.ValidationSandbox", lambda *args, **kwargs: mock_sandbox)

    pipeline_dynamic = OrchestrationPipeline(
        repo_path=str(tmp_path),
        reference_branch="main",
        target_commit="commit_def456",
        llm=False,
        validate=True,
    )
    final_state_dyn = pipeline_dynamic.run()
    assert final_state_dyn.checkpoint == "awaiting_human_review"
    assert final_state_dyn.suggestions[0].patch_combinations[0].validated is True


def test_build_langgraph_workflow_graceful_handling():
    # If langgraph is not installed, it should raise a clear ImportError
    try:
        import langgraph  # noqa: F401
        has_langgraph = True
    except ImportError:
        has_langgraph = False

    if not has_langgraph:
        with pytest.raises(ImportError, match="LangGraph is an optional dependency"):
            build_langgraph_workflow()
    else:
        graph = build_langgraph_workflow()
        assert graph is not None
