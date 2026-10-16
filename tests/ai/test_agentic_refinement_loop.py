"""Tests for the GDSS Agentic Refinement Loop in Orchestration Pipeline."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from gdss.ai.orchestration import (
    ConvergenceState,
    OrchestrationPipeline,
    refine_step,
    run_convergence_pipeline,
    should_refine,
)
from gdss.ai.types import (
    ConflictTopology,
    PatchCombination,
    Suggestion,
    SuggestionAnchor,
    SuggestionContext,
)


def _dummy_suggestion(file_path: str = "src/calc.py") -> Suggestion:
    anchor = SuggestionAnchor(
        file_path=file_path,
        line_start=1,
        line_end=5,
    )
    topology = ConflictTopology(
        kind="intersection",
        symbol_id=f"{file_path}::add",
        operator_i="modify_function",
        operator_j="modify_function",
        commutativity="interfere",
        justification="Overlapping modify",
    )
    combo = PatchCombination(
        label="reconcile",
        strategy="compose",
        patch_text="def add(a, b):\n    return SYNTAX_BROKEN\n",
        validated=False,
        validation_status="rejected",
        validation_error="SyntaxError: invalid syntax at line 2",
    )
    return Suggestion(
        kind="modify_function",
        file_path=file_path,
        line_start=1,
        line_end=5,
        symbol_id=f"{file_path}::add",
        operator="modify_function",
        action="reconcile changes",
        rationale="Overlapping modify",
        reason=("Same file", "Same function"),
        confidence=0.9,
        rank=1,
        topology=topology,
        patch_combinations=(combo,),
        anchor=anchor,
        context=SuggestionContext(
            reference_branch="main",
            candidate_branch="feature-a",
            omega=0.8,
            merge_risk=0.5,
            operator_i_id="op1",
            operator_j_id="op2",
            other_branch="feature-b",
        ),
    )


def test_should_refine_decision_logic():
    sug = _dummy_suggestion()
    state = ConvergenceState(
        repo_path="/tmp",
        llm=True,
        validate=True,
        provider=MagicMock(),
        suggestions=[sug],
        max_refinements=2,
        refinement_count=0,
    )
    assert should_refine(state) == "refine"

    # If retries exhausted -> checkpoint
    state.refinement_count = 2
    assert should_refine(state) == "checkpoint"

    # If validation is clean -> checkpoint
    state.refinement_count = 0
    clean_combo = PatchCombination(label="reconcile", strategy="compose", patch_text="clean", validated=True)
    state.suggestions[0] = Suggestion(
        kind="modify_function",
        file_path="src/calc.py",
        line_start=1,
        line_end=5,
        symbol_id="src/calc.py::add",
        operator="modify_function",
        action="reconcile",
        rationale="r",
        reason=("r",),
        confidence=0.9,
        patch_combinations=(clean_combo,),
    )
    assert should_refine(state) == "checkpoint"


def test_refinement_loop_recovers_and_validates(tmp_path: Path):
    (tmp_path / ".git").mkdir()

    sug = _dummy_suggestion()

    fixed_patch = "--- a/src/calc.py\n+++ b/src/calc.py\n@@ -1,3 +1,3 @@\n-def add(a, b):\n+def add(a, b, c=0):\n-    return a + b\n+    return a + b\n"

    mock_provider = MagicMock()
    mock_provider.complete.return_value = fixed_patch

    validation_calls = 0

    def mock_validator(patch: str, target: str, timeout: float | None) -> tuple[bool, str | None]:
        nonlocal validation_calls
        validation_calls += 1
        if "SYNTAX_BROKEN" in patch:
            return False, "Syntax error at line 2: unexpected EOF"
        return True, None

    state = ConvergenceState(
        repo_path=str(tmp_path),
        reference_branch="main",
        llm=True,
        validate=True,
        provider=mock_provider,
        validator=mock_validator,
        suggestions=[sug],
        max_refinements=2,
    )

    pipeline = OrchestrationPipeline(
        repo_path=str(tmp_path),
        reference_branch="main",
        llm=True,
        validate=True,
        provider=mock_provider,
        validator=mock_validator,
    )
    pipeline.state = state
    result = pipeline.run()

    assert result.checkpoint == "awaiting_human_review"
    assert result.refinement_count == 1
    assert len(result.refinement_history) == 1
    assert result.refinement_history[0]["strategy"] == "reconcile"
    assert result.refinement_history[0]["attempt"] == 1
    # Combinations should now be validated
    assert result.suggestions[0].patch_combinations[0].validated is True
    assert result.suggestions[0].patch_combinations[0].validation_status == "validated"


def test_refinement_loop_exhausts_retries_gracefully(tmp_path: Path):
    (tmp_path / ".git").mkdir()

    sug = _dummy_suggestion()

    mock_provider = MagicMock()
    mock_provider.complete.return_value = "--- a/src/calc.py\n+++ b/src/calc.py\nstill broken"

    def always_fail_validator(patch: str, target: str, timeout: float | None) -> tuple[bool, str | None]:
        return False, "Compiler error: broken syntax"

    state = ConvergenceState(
        repo_path=str(tmp_path),
        reference_branch="main",
        llm=True,
        validate=True,
        provider=mock_provider,
        validator=always_fail_validator,
        suggestions=[sug],
        max_refinements=2,
    )

    pipeline = OrchestrationPipeline(
        repo_path=str(tmp_path),
        reference_branch="main",
        llm=True,
        validate=True,
        provider=mock_provider,
        validator=always_fail_validator,
    )
    pipeline.state = state
    result = pipeline.run()

    # Reached checkpoint without infinite loop
    assert result.checkpoint == "awaiting_human_review"
    assert result.refinement_count == 2
    assert len(result.refinement_history) == 2
    assert result.suggestions[0].patch_combinations[0].validated is False


def test_run_convergence_pipeline_with_refinement(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    sug = _dummy_suggestion()

    mock_provider = MagicMock()
    mock_provider.complete.return_value = (
        "--- a/src/calc.py\n+++ b/src/calc.py\n@@ -1,3 +1,3 @@\n-def add(a, b):\n+def add(a, b):\n-    return SYNTAX_BROKEN\n+    return a + b\n"
    )

    def validator(patch: str, target: str, timeout: float | None) -> tuple[bool, str | None]:
        for line in patch.splitlines():
            if line.startswith("+") and "SYNTAX_BROKEN" in line:
                return False, "Syntax error"
        if patch.startswith("def ") and "SYNTAX_BROKEN" in patch:
            return False, "Syntax error"
        return True, None

    state = ConvergenceState(
        repo_path=str(tmp_path),
        reference_branch="main",
        llm=True,
        validate=True,
        provider=mock_provider,
        validator=validator,
        suggestions=[sug],
        max_refinements=2,
    )

    # Test single refine_step manually
    refined = refine_step(state)
    assert refined.checkpoint == "refined"
    assert refined.refinement_count == 1

    # Reset state and run via run_convergence_pipeline
    state2 = ConvergenceState(
        repo_path=str(tmp_path),
        reference_branch="main",
        llm=True,
        validate=True,
        provider=mock_provider,
        validator=validator,
        suggestions=[sug],
        max_refinements=2,
    )
    res = run_convergence_pipeline(state2, use_langgraph=False)
    assert res.checkpoint == "awaiting_human_review"
    assert res.refinement_count == 1
    assert res.suggestions[0].patch_combinations[0].validated is True


def test_langgraph_refinement_parity(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    sug = _dummy_suggestion()

    mock_provider = MagicMock()
    mock_provider.complete.return_value = (
        "--- a/src/calc.py\n+++ b/src/calc.py\n@@ -1,3 +1,3 @@\n-def add(a, b):\n+def add(a, b):\n-    return SYNTAX_BROKEN\n+    return a + b\n"
    )

    def validator(patch: str, target: str, timeout: float | None) -> tuple[bool, str | None]:
        for line in patch.splitlines():
            if line.startswith("+") and "SYNTAX_BROKEN" in line:
                return False, "Syntax error"
        if patch.startswith("def ") and "SYNTAX_BROKEN" in patch:
            return False, "Syntax error"
        return True, None

    state = ConvergenceState(
        repo_path=str(tmp_path),
        reference_branch="main",
        llm=True,
        validate=True,
        provider=mock_provider,
        validator=validator,
        suggestions=[sug],
        max_refinements=2,
    )

    res = run_convergence_pipeline(state, use_langgraph=True)
    assert res.checkpoint == "awaiting_human_review"
    assert res.refinement_count == 1
    assert res.suggestions[0].patch_combinations[0].validated is True


