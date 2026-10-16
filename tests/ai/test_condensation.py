"""Unit tests for 3-tier model context window discovery and adaptive AST condensation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from gdss.ai.condensation import (
    condense_block,
    get_model_code_budget,
    resolve_context_window,
)


def test_resolve_context_window_tier1_user_override():
    # User override in argument takes priority
    assert resolve_context_window("gpt-4o", user_override=65536) == 65536

    # Environment variable override takes priority over heuristics
    with patch.dict("os.environ", {"GDSS_CONTEXT_WINDOW": "32000"}):
        assert resolve_context_window("gpt-4o") == 32000


def test_resolve_context_window_tier2_provider_api():
    # Mock OpenRouter provider
    mock_openrouter = MagicMock()
    mock_openrouter.base_url = "https://openrouter.ai/api/v1"
    mock_openrouter.api_key = "test-key"

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {
        "data": [
            {"id": "anthropic/claude-3-opus", "context_length": 200000},
            {"id": "meta-llama/llama-3.1-8b", "context_length": 131072},
        ]
    }

    with patch("httpx.get", return_value=fake_resp):
        res = resolve_context_window("meta-llama/llama-3.1-8b", provider=mock_openrouter)
        assert res == 131072

    # Mock Ollama provider
    mock_ollama = MagicMock()
    mock_ollama.host = "http://localhost:11434"
    mock_ollama.model = "qwen2.5-coder:7b"

    fake_ollama_resp = MagicMock()
    fake_ollama_resp.status_code = 200
    fake_ollama_resp.json.return_value = {
        "model_info": {
            "qwen2.context_length": 32768,
        }
    }

    with patch("httpx.post", return_value=fake_ollama_resp):
        res = resolve_context_window("qwen2.5-coder:7b", provider=mock_ollama)
        assert res == 32768


def test_resolve_context_window_tier3_heuristics():
    # OpenAI and Copilot models (no API context window)
    assert resolve_context_window("gpt-4o") == 128000
    assert resolve_context_window("gpt-4o-mini") == 128000
    assert resolve_context_window("o1-mini") == 128000
    assert resolve_context_window("claude-3-5-sonnet-20241022") == 200000
    assert resolve_context_window("deepseek-chat") == 64000
    assert resolve_context_window("qwen2.5-coder:32b") == 32768
    assert resolve_context_window("llama-3.1-8b-instruct") == 128000

    # Unrecognized model falls back to safe 16k default
    assert resolve_context_window("custom-finetuned-unknown") == 16384
    assert resolve_context_window(None) == 16384


def test_get_model_code_budget():
    # 128k model gives ~400k character budget
    budget_128k = get_model_code_budget("gpt-4o")
    assert budget_128k >= 400000

    # 16k model gives ~25k character budget
    budget_16k = get_model_code_budget("custom-unknown")
    assert 20000 <= budget_16k <= 30000


def test_condense_block_respects_dynamic_budget():
    mock_context = MagicMock()
    mock_suggestion = MagicMock()
    mock_suggestion.anchor = None

    small_block = "def foo():\n    return 42\n"
    # Small block under budget is untouched
    condensed = condense_block(mock_context, mock_suggestion, small_block, max_chars=1000)
    assert condensed == small_block
