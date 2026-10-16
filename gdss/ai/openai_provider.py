"""OpenAI-compatible LLM provider with an on-disk prompt cache."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

import httpx


class OpenAICompatibleProvider:
    """Provider for OpenAI-compatible Chat Completion APIs (OpenAI, GitHub Models, Azure, vLLM)."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        cache_dir: Path | None = None,
        timeout: float = 120.0,
    ) -> None:
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        github_token = os.getenv("GITHUB_TOKEN")
        token = api_key or openrouter_key or openai_key or github_token
        self.api_key = token

        # Base URL resolution
        url = base_url or os.getenv("OPENAI_BASE_URL")
        if not url:
            if openrouter_key and not openai_key and not github_token:
                url = "https://openrouter.ai/api/v1"
            elif github_token and not openai_key:
                url = "https://models.inference.ai.azure.com"
            else:
                url = "https://api.openai.com/v1"
        self.base_url = url.rstrip("/")

        # Model resolution
        if "openrouter.ai" in self.base_url:
            default_model = "qwen/qwen-2.5-coder-32b-instruct"
        elif "azure.com" in self.base_url or "openai.com" in self.base_url:
            default_model = "gpt-4o-mini"
        else:
            default_model = "default"

        self.model = (
            model
            or os.getenv("OPENROUTER_MODEL")
            or os.getenv("OPENAI_MODEL")
            or os.getenv("GITHUB_MODEL")
            or default_model
        )
        self.cache_dir = cache_dir or Path(".gdss/llm_cache")
        self.timeout = timeout

    def complete(self, prompt: str, *, temperature: float = 0.0, max_tokens: int = -1) -> str:
        """Call OpenAI-compatible chat endpoint and return reply."""
        cache_key = hashlib.sha256(f"{self.model}:{prompt}".encode()).hexdigest()
        cache_path = self.cache_dir / cache_key
        if cache_path.exists():
            return cache_path.read_text(encoding="utf-8")

        endpoint = self.base_url
        if endpoint.endswith("/v1"):
            api_url = f"{endpoint}/chat/completions"
        else:
            api_url = f"{endpoint}/v1/chat/completions"

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if "openrouter.ai" in self.base_url:
            headers["HTTP-Referer"] = "https://github.com/Sarthak2233/GDSS"
            headers["X-Title"] = "GDSS"

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if max_tokens > 0:
            payload["max_tokens"] = max_tokens

        response = httpx.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"]

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(text, encoding="utf-8")
        return text
