from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from gdss.ai.openai_provider import OpenAICompatibleProvider
from gdss.ai.vllm_provider import VLLMProvider


def test_openai_compatible_provider_defaults_to_github_models(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test12345")

    provider = OpenAICompatibleProvider(cache_dir=tmp_path)
    assert provider.base_url == "https://models.inference.ai.azure.com"
    assert provider.api_key == "ghp_test12345"
    assert provider.model == "gpt-4o-mini"


def test_openai_compatible_provider_custom_config(tmp_path: Path) -> None:
    provider = OpenAICompatibleProvider(
        base_url="https://api.mycustomai.com/v1",
        model="custom-coder",
        api_key="secret-key",
        cache_dir=tmp_path,
    )
    assert provider.base_url == "https://api.mycustomai.com/v1"
    assert provider.model == "custom-coder"
    assert provider.api_key == "secret-key"


def test_openai_compatible_provider_complete_and_cache(tmp_path: Path) -> None:
    provider = OpenAICompatibleProvider(
        base_url="http://test-server/v1",
        model="test-model",
        api_key="test-key",
        cache_dir=tmp_path,
    )

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "def test(): return 42"}}]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_response) as mock_post:
        first_call = provider.complete("generate code")
        assert first_call == "def test(): return 42"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["headers"]["Authorization"] == "Bearer test-key"
        assert call_kwargs["json"]["model"] == "test-model"

        # Second call with same prompt should hit cache without posting again
        second_call = provider.complete("generate code")
        assert second_call == "def test(): return 42"
        assert mock_post.call_count == 1


def test_vllm_provider_inherits_openai_compatible(tmp_path: Path) -> None:
    provider = VLLMProvider(cache_dir=tmp_path)
    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == "http://localhost:8000"
    assert provider.model == "qwen2.5-coder-7b"


def test_openai_compatible_provider_openrouter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-testkey")
    monkeypatch.setenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")

    provider = OpenAICompatibleProvider(cache_dir=tmp_path)
    assert provider.base_url == "https://openrouter.ai/api/v1"
    assert provider.api_key == "sk-or-v1-testkey"
    assert provider.model == "meta-llama/llama-3.3-70b-instruct"

    mock_response = MagicMock()
    mock_response.json.return_value = {"choices": [{"message": {"content": "openrouter response"}}]}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_response) as mock_post:
        reply = provider.complete("hello")
        assert reply == "openrouter response"
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["headers"]["Authorization"] == "Bearer sk-or-v1-testkey"
        assert call_kwargs["headers"]["HTTP-Referer"] == "https://github.com/Sarthak2233/GDSS"
        assert call_kwargs["headers"]["X-Title"] == "GDSS"
