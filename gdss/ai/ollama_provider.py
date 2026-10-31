"""Local-only Ollama provider with an on-disk prompt cache."""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx


class OllamaProvider:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "qwen2.5-coder:7b",
        cache_dir: Path | None = None,
    ) -> None:
        from gdss.ai.model_manager import ModelManager

        # Validate base_url via ModelManager
        _ = ModelManager(base_url)
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.cache_dir = cache_dir or Path(".gdss/llm_cache")

    def complete(self, prompt: str, *, temperature: float = 0.0, max_tokens: int = -1) -> str:
        key = hashlib.sha256(prompt.encode()).hexdigest()
        cached = self.cache_dir / key
        if cached.exists():
            return cached.read_text(encoding="utf-8")
        response = httpx.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "stream": False,
                "messages": [{"role": "user", "content": prompt}],
                "options": {"temperature": temperature, "num_predict": max_tokens},
            },
            timeout=120.0,
        )
        response.raise_for_status()
        text = response.json()["message"]["content"]
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cached.write_text(text, encoding="utf-8")
        return text
