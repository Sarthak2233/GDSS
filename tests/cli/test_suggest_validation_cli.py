"""Tests for gdss suggest CLI validation options."""

from __future__ import annotations

from typer.testing import CliRunner

from gdss.cli.main import app

runner = CliRunner()


def test_suggest_help_displays_validation_options():
    res = runner.invoke(app, ["suggest", "--help"])
    assert res.exit_code == 0
    assert "--validate" in res.output
    assert "--sandbox-timeout" in res.output
    assert "--context-window" in res.output
    assert "--max-refinements" in res.output


def test_suggest_context_window_sets_env(monkeypatch):
    from unittest.mock import patch

    with patch("gdss.ai.suggester.suggest", return_value=[]):
        res = runner.invoke(app, ["suggest", "--context-window", "65536"])
        assert res.exit_code == 0
        import os

        assert os.environ.get("GDSS_CONTEXT_WINDOW") == "65536"


def test_suggest_validate_routes_through_convergence_pipeline():
    from unittest.mock import patch

    from gdss.ai.orchestration import ConvergenceState

    mock_state = ConvergenceState(
        repo_path=".",
        suggestions=[],
    )
    with patch(
        "gdss.ai.orchestration.run_convergence_pipeline", return_value=mock_state
    ) as mock_pipe:
        res = runner.invoke(app, ["suggest", "--validate", "--max-refinements", "4"])
        assert res.exit_code == 0
        assert mock_pipe.called
        call_arg = mock_pipe.call_args[0][0]
        assert call_arg.validate is True
        assert call_arg.max_refinements == 4


def test_suggest_as_prompt_injects_intent_and_commits():
    from unittest.mock import MagicMock, patch

    from gdss.ai.types import Suggestion, SuggestionAnchor

    mock_sug = Suggestion(
        kind="reconcile",
        file_path="service.py",
        line_start=1,
        line_end=5,
        symbol_id="process",
        operator="modify_function",
        action="reconcile process",
        rationale="Overlapping changes",
        reason=("collision",),
        confidence=0.9,
        anchor=SuggestionAnchor(
            file_path="service.py",
            target_branch="feature",
            line_start=1,
            line_end=5,
        ),
    )
    mock_ctx = MagicMock()
    mock_ctx.branch_commits = {"feature": [{"sha": "abc1234", "summary": "Fix payment"}]}
    mock_ctx.branch_intents = {"feature": {"title": "Payment overhaul"}}
    mock_ctx.observer.get_file_content_at_commit.return_value = "def process(): pass\n"

    with patch("gdss.ai.suggester.suggest", return_value=[mock_sug]):
        with patch("gdss.ai.context.build_analysis_context", return_value=mock_ctx):
            with patch(
                "gdss.ai.prompt_builder.build_conflict_prompt", return_value="PROMPT_WITH_INTENT"
            ) as mock_prompt_builder:
                res = runner.invoke(app, ["suggest", "--as-prompt"])
                assert res.exit_code == 0
                assert "PROMPT_WITH_INTENT" in res.output
                assert mock_prompt_builder.called
                kwargs = mock_prompt_builder.call_args.kwargs
                assert kwargs["branch_commits"] == mock_ctx.branch_commits
                assert kwargs["branch_intents"] == mock_ctx.branch_intents
                assert kwargs.get("collision_context") is not None
