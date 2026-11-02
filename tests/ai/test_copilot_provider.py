"""Tests for CopilotCLIProvider adapter and tool denial enforcement."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gdss.ai.copilot_provider import CopilotCLIProvider
from gdss.ai.suggester import _pick_provider


def test_copilot_provider_binary_discovery(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/copilot" if name == "copilot" else None)
    provider = CopilotCLIProvider(cache_dir=tmp_path)
    assert provider.is_available() is True
    assert provider._bin == "/usr/local/bin/copilot"

    monkeypatch.setattr("shutil.which", lambda name: None)
    provider_unavailable = CopilotCLIProvider(cache_dir=tmp_path)
    assert provider_unavailable.is_available() is False


def test_copilot_provider_complete_enforces_safe_tool_denial(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/copilot")
    provider = CopilotCLIProvider(model="claude-3.5-sonnet", cache_dir=tmp_path)

    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = "```python\ndef test(): return 42\n```"
    mock_res.stderr = ""

    with patch("subprocess.run", return_value=mock_res) as mock_run:
        result = provider.complete("Write test function")
        assert result == "```python\ndef test(): return 42\n```"
        mock_run.assert_called_once()

        cmd = mock_run.call_args[0][0]
        # Critical security assertions: tools must be denied and non-interactive flags set
        assert "/usr/local/bin/copilot" in cmd
        assert "-p" in cmd
        assert "--silent" in cmd
        assert "--no-ask-user" in cmd
        assert "--deny-tool=*" in cmd
        assert "--model" in cmd
        assert "claude-3.5-sonnet" in cmd

        # Second call with same prompt hits disk cache
        cached_result = provider.complete("Write test function")
        assert cached_result == "```python\ndef test(): return 42\n```"
        assert mock_run.call_count == 1


def test_copilot_provider_handles_non_zero_exit_gracefully(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    import logging

    monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/copilot")
    provider = CopilotCLIProvider(cache_dir=tmp_path)

    mock_res = MagicMock()
    mock_res.returncode = 1
    mock_res.stdout = ""
    mock_res.stderr = "403 Forbidden: Account not entitled for Copilot CLI CI requests"

    with caplog.at_level(logging.WARNING), patch("subprocess.run", return_value=mock_res):
        output = provider.complete("Generate patch")
        assert output == ""
        assert "Copilot CLI returned non-zero exit code 1" in caplog.text
        assert "403 Forbidden" in caplog.text


def test_copilot_provider_handles_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    import logging

    monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/copilot")
    provider = CopilotCLIProvider(cache_dir=tmp_path, timeout=5.0)

    with caplog.at_level(logging.WARNING), patch(
        "subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["copilot"], timeout=5.0)
    ):
        output = provider.complete("Generate complex patch")
        assert output == ""
        assert "Copilot CLI inference timed out" in caplog.text


def test_copilot_provider_not_found_raises_runtime_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("shutil.which", lambda name: None)
    provider = CopilotCLIProvider(cache_dir=tmp_path)

    with pytest.raises(RuntimeError, match="Copilot CLI binary not found in PATH"):
        provider.complete("Generate patch")


def test_suggester_resolves_copilot_string_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/copilot")
    prov = _pick_provider(llm=True, provider="copilot")
    assert isinstance(prov, CopilotCLIProvider)
    assert prov.model == "gpt-4o"

