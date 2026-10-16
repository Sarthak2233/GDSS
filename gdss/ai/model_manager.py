"""Model lifecycle management for local Ollama providers."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from typing import Any
from urllib.parse import urlparse

import httpx


class ModelManagerError(Exception):
    pass


class ModelManager:
    """Manages the lifecycle of local LLM models via Ollama."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434") -> None:
        host = urlparse(base_url).hostname
        if host not in {"127.0.0.1", "localhost", "::1"} and os.getenv("GDSS_LLM_ALLOW_REMOTE") != "1":
            raise ValueError("Ollama base URL must be localhost unless GDSS_LLM_ALLOW_REMOTE=1")
        self.base_url = base_url.rstrip("/")

    def status(self) -> dict[str, str]:
        """Check if the Ollama service is reachable."""
        try:
            response = httpx.get(f"{self.base_url}/api/version", timeout=5.0)
            response.raise_for_status()
            return {"status": "ok", "version": response.json().get("version", "unknown")}
        except Exception as e:
            raise ModelManagerError(f"Ollama service unreachable: {e}") from e

    def list_models(self) -> list[dict[str, Any]]:
        """List locally available models."""
        try:
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            response.raise_for_status()
            return response.json().get("models", [])
        except Exception as e:
            raise ModelManagerError(f"Failed to list models: {e}") from e

    def pull_model(self, model: str) -> Iterator[dict[str, Any]]:
        """Pull a model from the Ollama registry, yielding progress dicts."""
        try:
            with httpx.stream(
                "POST",
                f"{self.base_url}/api/pull",
                json={"name": model, "stream": True},
                timeout=None
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        yield json.loads(line)
        except Exception as e:
            raise ModelManagerError(f"Failed to pull model '{model}': {e}") from e

    def remove_model(self, model: str) -> None:
        """Remove a model from the local Ollama registry."""
        try:
            response = httpx.request(
                "DELETE",
                f"{self.base_url}/api/delete",
                json={"name": model},
                timeout=10.0
            )
            response.raise_for_status()
        except Exception as e:
            raise ModelManagerError(f"Failed to remove model '{model}': {e}") from e
