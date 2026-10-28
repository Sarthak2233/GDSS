"""Provider boundary for optional LLM patch drafting."""

from __future__ import annotations

from typing import Protocol

from gdss.ai.ollama_provider import OllamaProvider
from gdss.ai.openai_provider import OpenAICompatibleProvider
from gdss.ai.vllm_provider import VLLMProvider


class LLMProvider(Protocol):
    def complete(self, prompt: str, *, temperature: float = 0.0, max_tokens: int = -1) -> str: ...


class StubProvider:
    """In-memory provider for deterministic tests; performs no network I/O."""

    def __init__(self, response: str) -> None:
        self.response = response

    def complete(self, prompt: str, *, temperature: float = 0.0, max_tokens: int = -1) -> str:
        _ = (prompt, temperature, max_tokens)
        return self.response


AnyProvider = OllamaProvider | VLLMProvider | OpenAICompatibleProvider | StubProvider
