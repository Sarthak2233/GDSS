"""Tests for AI Orchestration PR Audit Pipeline Integration.

Verifies:
1. Multi-branch AnalysisContext construction for PR refs against base
2. LangGraph / Pure-Python Convergence State Machine execution
3. Ephemeral sandbox validation and suggestion persistence in .gdss/suggestions/
4. Sticky comment Markdown rendering with topology badges and 1-click commit suggestions
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from gdss.ai.context import build_pr_analysis_context
from gdss.ai.orchestration import ConvergenceState, run_convergence_pipeline
from gdss.ai.suggestion_store import load_suggestion
from gdss.ai.types import ConflictTopology, PatchCombination, Suggestion, SuggestionAnchor
from gdss.core.transform_types import OperatorType, SemanticOperator
from gdss.validation.pr_audit import (
    STICKY_SIGNATURE,
    PRAuditContext,
    PRCollisionDetail,
    PRCollisionResult,
    audit_pr_collisions,
    render_radar_markdown,
)


def test_build_pr_analysis_context_multi_branch(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    cur_ops = [
        SemanticOperator(operator=OperatorType.MODIFY_FUNCTION, file="auth.py", name="login")
    ]
    oth_ops = [
        SemanticOperator(operator=OperatorType.MODIFY_FUNCTION, file="auth.py", name="login")
    ]

    pr_intents = {
        "feat-current": {"title": "Current PR", "description": "Fix bug", "author": "alice"},
        "feat-other": {"title": "Other PR", "description": "Feature work", "author": "bob"},
    }
    with patch("git.Repo"):
        with patch("gdss.watcher.git_observer.GitObserver.is_valid", return_value=True):
            with patch(
                "gdss.watcher.git_observer.GitObserver.get_commits_between",
                return_value=[
                    {
                        "sha": "12345678",
                        "summary": "mock commit",
                        "author": "alice",
                        "message": "mock commit",
                    }
                ],
            ):
                with patch(
                    "gdss.core.trajectory.extract_trajectory_operators",
                    side_effect=[cur_ops, oth_ops],
                ):
                    ctx = build_pr_analysis_context(
                        repo_path=str(tmp_path),
                        reference_branch="main",
                        current_pr_branch="feat-current",
                        concurrent_branches=["feat-other"],
                        pr_intents=pr_intents,
                    )
                    assert ctx.reference_branch == "main"
                    assert ctx.active_branch == "feat-current"
                    assert "feat-current" in ctx.branches
                    assert "feat-other" in ctx.branches
                    assert len(ctx.branch_operators["feat-current"]) == 1
                    assert len(ctx.branch_operators["feat-other"]) == 1
                    assert ctx.tensor is not None
                    assert "feat-current" in ctx.branch_intents
                    assert ctx.branch_intents["feat-current"]["title"] == "Current PR"
                    assert "feat-current" in ctx.branch_commits
                    assert len(ctx.branch_commits["feat-current"]) == 1


def test_run_convergence_pipeline_state_machine(tmp_path: Path):
    (tmp_path / ".git").mkdir()

    # Create dummy suggestion
    anchor = SuggestionAnchor(
        file_path="src/service.py",
        line_start=10,
        line_end=15,
    )
    sug = Suggestion(
        kind="modify_function",
        file_path="src/service.py",
        line_start=10,
        line_end=15,
        symbol_id="src/service.py::handle_request",
        operator="modify_function",
        action="reconcile changes",
        rationale="Overlapping modify",
        reason=("Same file", "Same function"),
        confidence=0.9,
        rank=1,
        topology=ConflictTopology(
            kind="intersection",
            symbol_id="src/service.py::handle_request",
            operator_i="modify_function",
            operator_j="modify_function",
            commutativity="interfere",
            justification="Same function modified",
        ),
        patch_combinations=(
            PatchCombination(
                label="reconcile",
                strategy="compose",
                patch_text="def handle_request(req, timeout=30):\n    return True\n",
            ),
        ),
        anchor=anchor,
    )

    state = ConvergenceState(
        repo_path=str(tmp_path),
        reference_branch="main",
        llm=False,
        validate=True,
        target_commit="commit123",
        validator=lambda patch, target, timeout: (True, None),
    )
    state.suggestions = [sug]

    # Run state machine
    res_state = run_convergence_pipeline(state)
    assert res_state.checkpoint == "awaiting_human_review"
    assert len(res_state.suggestions) == 1
    assert res_state.suggestions[0].validated is True
    assert res_state.suggestions[0].patch_combinations[0].validated is True

    # Confirm suggestion is saved in .gdss/suggestions/
    saved_data = load_suggestion(res_state.suggestions[0].suggestion_id, tmp_path)
    assert saved_data is not None
    assert saved_data["target_commit"] == "commit123"
    assert saved_data["file_path"] == "src/service.py"


def test_render_radar_markdown_topology_and_suggestion_details():
    ctx = PRAuditContext(
        repo_owner="org",
        repo_name="repo",
        pr_number=100,
        base_ref="main",
        head_ref="branch-100",
        head_sha="sha100",
        github_token="tok",
    )

    col = PRCollisionDetail(
        colliding_pr=99,
        author="developer",
        branch="branch-99",
        target_file="pkg/router.py",
        overlapping_symbol="route()",
        risk=0.88,
        description="Semantic collision on router definition.",
        merge_order_recommendation="Merge PR #99 first, then rebase PR #100.",
        suggestion_code="def route(path: str, auth: bool = True):\n    pass\n",
        topology_kind="asymmetric",
        suggestion_id="sug_deadbeef12345678",
        strategy_label="reconcile",
        reasons=["branch-99 adds parameter auth", "branch-100 calls route without auth"],
    )

    result = PRCollisionResult(
        current_pr=100,
        has_collisions=True,
        max_risk=0.88,
        collisions=[col],
        audited_prs_count=1,
    )

    md = render_radar_markdown(ctx, result)
    assert STICKY_SIGNATURE in md
    assert "🛰️ GDSS PR Collision Radar" in md
    assert "pkg/router.py" in md
    assert "#99 by @developer" in md
    assert "📐 Asymmetric" in md
    assert "0.88 (Critical)" in md
    assert "sug_deadbeef12345678" in md
    assert "gdss apply sug_deadbeef12345678 --strategy reconcile" in md
    assert "```suggestion" in md
    assert "def route(path: str, auth: bool = True):" in md
    assert "Commit suggestion" in md


def test_audit_pr_collisions_full_orchestration_flow(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    ctx = PRAuditContext(
        repo_owner="org",
        repo_name="repo",
        pr_number=10,
        base_ref="main",
        head_ref="feature-a",
        head_sha="sha_a",
        github_token="tok",
    )

    concurrent_prs = [
        {
            "number": 9,
            "title": "PR 9",
            "author": "bob",
            "head_ref": "feature-b",
            "head_sha": "sha_b",
            "base_ref": "main",
        }
    ]

    cur_ops = [
        SemanticOperator(operator=OperatorType.MODIFY_FUNCTION, file="auth.py", name="login")
    ]
    oth_ops = [
        SemanticOperator(operator=OperatorType.MODIFY_FUNCTION, file="auth.py", name="login")
    ]

    mock_patch = "def login(user, timeout=30): return True\n"

    with patch("git.Repo"):
        with patch("gdss.watcher.git_observer.GitObserver.is_valid", return_value=True):
            with patch(
                "gdss.core.trajectory.extract_trajectory_operators",
                side_effect=[cur_ops, oth_ops],
            ):
                with patch(
                    "gdss.validation.pr_audit.generate_pr_convergence_patch",
                    return_value=mock_patch,
                ):
                    result = audit_pr_collisions(str(tmp_path), ctx, concurrent_prs)
                    assert result.has_collisions is True
                    assert result.max_risk >= 0.5
                    assert len(result.collisions) == 1
                    col = result.collisions[0]
                    assert col.colliding_pr == 9
                    assert col.author == "bob"
                    assert col.suggestion_code == mock_patch
