import pytest

from gdss.ai.ollama_provider import OllamaProvider


def test_ollama_provider_rejects_remote_host_without_opt_in(monkeypatch):
    monkeypatch.delenv("GDSS_LLM_ALLOW_REMOTE", raising=False)
    with pytest.raises(ValueError, match="localhost"):
        OllamaProvider("http://example.com")
