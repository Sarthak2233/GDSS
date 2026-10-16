"""Local VLLM provider with on-disk prompt caching (subclasses OpenAICompatibleProvider)."""

from __future__ import annotations

import os
from pathlib import Path

from gdss.ai.openai_provider import OpenAICompatibleProvider


class VLLMProvider(OpenAICompatibleProvider):
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        model: str | None = None,
        cache_dir: Path | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            model=model or os.getenv("VLLM_MODEL", "qwen2.5-coder-7b"),
            api_key=os.getenv("VLLM_API_KEY"),
            cache_dir=cache_dir,
        )
