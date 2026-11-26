"""Tests for gdss suggest CLI and Web API configuration resolution from .gdss.yml and .env."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from gdss.cli.main import app

runner = CliRunner()


def test_suggest_resolves_config_from_gdss_yml(tmp_path: Path):
    """Verifies that gdss suggest falls back to .gdss.yml when CLI flags are default."""
    config_file = tmp_path / ".gdss.yml"
    config_file.write_text(
        """
radar:
  provider: "openrouter"
  model: "anthropic/claude-3.5-sonnet"
  context_window: 64000
  max_refinements: 5
  concurrency_limit: 8
  condensation: "ast_minimal"
  include:
    - "feature/*"
  exclude:
    - "spike/*"
""",
        encoding="utf-8",
    )

    env_file = tmp_path / ".env"
    env_file.write_text("OPENROUTER_API_KEY=test-mock-key-from-dotenv\n", encoding="utf-8")

    captured_state = {}

    def mock_run_convergence_pipeline(state):
        captured_state["model"] = getattr(state.provider, "model", None) if state.provider else None
        captured_state["max_refinements"] = state.max_refinements
        captured_state["concurrency_limit"] = state.concurrency_limit
        captured_state["condensation_mode"] = state.condensation_mode
        captured_state["branches"] = state.branches
        captured_state["exclude_branches"] = state.exclude_branches
        res = MagicMock()
        res.suggestions = []
        return res

    with patch("gdss.ai.orchestration.run_convergence_pipeline", side_effect=mock_run_convergence_pipeline):
        res = runner.invoke(app, ["suggest", "--repo", str(tmp_path), "--llm", "--validate"])
        assert res.exit_code == 0

    assert captured_state["model"] == "anthropic/claude-3.5-sonnet"
    assert captured_state["max_refinements"] == 5
    assert captured_state["concurrency_limit"] == 8
    assert captured_state["condensation_mode"] == "ast_minimal"
    assert captured_state["branches"] == ["feature/*"]
    assert captured_state["exclude_branches"] == ["spike/*"]


def test_suggest_cli_explicit_flags_override_gdss_yml(tmp_path: Path):
    """Verifies that explicit CLI flags override .gdss.yml settings."""
    config_file = tmp_path / ".gdss.yml"
    config_file.write_text(
        """
radar:
  provider: "openrouter"
  model: "anthropic/claude-3.5-sonnet"
  max_refinements: 5
""",
        encoding="utf-8",
    )

    captured_state = {}

    def mock_run_convergence_pipeline(state):
        captured_state["model"] = getattr(state.provider, "model", None) if state.provider else None
        captured_state["max_refinements"] = state.max_refinements
        res = MagicMock()
        res.suggestions = []
        return res

    with patch("gdss.ai.orchestration.run_convergence_pipeline", side_effect=mock_run_convergence_pipeline):
        res = runner.invoke(
            app,
            [
                "suggest",
                "--repo",
                str(tmp_path),
                "--llm",
                "--validate",
                "--model",
                "custom-override-model",
                "--max-refinements",
                "7",
            ],
            env={"OPENROUTER_API_KEY": "test-key"},
        )
        assert res.exit_code == 0

    assert captured_state["model"] == "custom-override-model"
    assert captured_state["max_refinements"] == 7


def test_web_service_get_suggestions_resolves_config(tmp_path: Path):
    """Verifies that gdss.api.service.get_suggestions loads config and provider."""
    from gdss.api import service

    config_file = tmp_path / ".gdss.yml"
    config_file.write_text(
        """
radar:
  provider: "openrouter"
  model: "deepseek/deepseek-coder"
  include:
    - "feat/*"
""",
        encoding="utf-8",
    )

    captured_suggest_kwargs = {}

    def mock_suggest(*args, **kwargs):
        captured_suggest_kwargs.update(kwargs)
        return []

    with patch("gdss.ai.suggester.suggest", side_effect=mock_suggest):
        res = service.get_suggestions(str(tmp_path), llm=True)
        assert res["status"] == "ok"

    assert captured_suggest_kwargs["branches"] == ["feat/*"]
    assert captured_suggest_kwargs["llm"] is True
    provider = captured_suggest_kwargs["provider"]
    assert provider is not None
    assert getattr(provider, "model", None) == "deepseek/deepseek-coder"
