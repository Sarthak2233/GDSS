"""OpenAI-compatible LLM provider with an on-disk prompt cache."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx

from gdss.logger import get_logger

logger = get_logger("gdss.ai.openai_provider")


class OpenAICompatibleProvider:
    """Provider for OpenAI-compatible Chat Completion APIs (OpenRouter, DeepSeek, Groq, Together, Mistral, Anthropic, Gemini, Cohere, Perplexity, Azure AI, OpenAI, vLLM, Ollama)."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        cache_dir: Path | None = None,
        timeout: float = 120.0,
        api_key_env: str | None = None,
    ) -> None:
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        azure_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_AI_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")
        together_key = os.getenv("TOGETHER_API_KEY")
        mistral_key = os.getenv("MISTRAL_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY")
        cohere_key = os.getenv("COHERE_API_KEY")
        perplexity_key = os.getenv("PERPLEXITY_API_KEY")

        # Base URL resolution
        url = (
            base_url
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("AZURE_OPENAI_ENDPOINT")
            or os.getenv("AZURE_AI_ENDPOINT")
        )
        if not url:
            from gdss.core.config import resolve_provider_base_url

            url = resolve_provider_base_url(None) or "https://api.openai.com/v1"

        if "models.inference.ai.azure.com" in url or "models.github.ai" in url:
            logger.warning(
                "GitHub Models (%s) was retired on July 30, 2026. This endpoint is no longer "
                "operational (HTTP 410 Gone). Please migrate to Microsoft Azure AI Foundry "
                "(https://<resource>.openai.azure.com/openai/v1), OpenRouter, or local Ollama.",
                url,
            )

        self.base_url = url.rstrip("/")

        # Strict provider-aware API key resolution (prevents cross-key contamination)
        token = api_key
        if not token:
            custom_key = os.getenv(api_key_env) if api_key_env else None
            gdss_key = os.getenv("GDSS_API_KEY")
            if custom_key:
                token = custom_key
            elif gdss_key:
                token = gdss_key
            elif "openrouter.ai" in self.base_url:
                token = openrouter_key
            elif "deepseek.com" in self.base_url:
                token = deepseek_key
            elif "groq.com" in self.base_url:
                token = groq_key
            elif "together.xyz" in self.base_url or "together.ai" in self.base_url:
                token = together_key
            elif "mistral.ai" in self.base_url:
                token = mistral_key
            elif "anthropic.com" in self.base_url:
                token = anthropic_key
            elif "generativelanguage.googleapis.com" in self.base_url:
                token = gemini_key
            elif "cohere.ai" in self.base_url:
                token = cohere_key
            elif "perplexity.ai" in self.base_url:
                token = perplexity_key
            elif "azure.com" in self.base_url:
                token = azure_key
            elif "openai.com" in self.base_url:
                token = openai_key
            else:
                token = (
                    openrouter_key
                    or deepseek_key
                    or groq_key
                    or openai_key
                    or azure_key
                    or together_key
                    or mistral_key
                    or anthropic_key
                    or gemini_key
                    or cohere_key
                    or perplexity_key
                )

        self.api_key = token

        # Model resolution defaults per provider
        if "openrouter.ai" in self.base_url:
            default_model = "openrouter/free"
        elif "deepseek.com" in self.base_url:
            default_model = "deepseek-chat"
        elif "groq.com" in self.base_url:
            default_model = "llama-3.3-70b-versatile"
        elif "together" in self.base_url:
            default_model = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
        elif "mistral.ai" in self.base_url:
            default_model = "codestral-latest"
        elif "anthropic.com" in self.base_url:
            default_model = "claude-3-5-sonnet-20241022"
        elif "generativelanguage.googleapis.com" in self.base_url:
            default_model = "gemini-2.0-flash"
        elif "cohere.ai" in self.base_url:
            default_model = "command-r-plus"
        elif "perplexity.ai" in self.base_url:
            default_model = "sonar-pro"
        elif "azure.com" in self.base_url or "openai.com" in self.base_url:
            default_model = "gpt-4o-mini"
        else:
            default_model = "default"

        self.model = (
            model
            or os.getenv("OPENROUTER_MODEL")
            or os.getenv("AZURE_OPENAI_MODEL")
            or os.getenv("OPENAI_MODEL")
            or default_model
        )
        self.cache_dir = cache_dir or Path(".gdss/llm_cache")
        self.timeout = timeout

    def _build_api_url(self) -> str:
        """Construct the exact chat completions endpoint URL with query params support."""
        url = self.base_url.strip()
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")

        if "/chat/completions" in path:
            new_path = path
        elif path.endswith("/v1") or path.endswith("/openai") or "/v1/" in path or "/openai/" in path:
            new_path = f"{path}/chat/completions"
        elif path == "" or path == "/":
            new_path = "/v1/chat/completions"
        else:
            new_path = f"{path}/v1/chat/completions"

        return urlunparse(
            (parsed.scheme, parsed.netloc, new_path, parsed.params, parsed.query, parsed.fragment)
        )

    def complete(self, prompt: str, *, temperature: float = 0.0, max_tokens: int = -1) -> str:
        """Call OpenAI-compatible chat endpoint and return reply."""
        cache_key = hashlib.sha256(f"{self.model}:{prompt}".encode()).hexdigest()
        cache_path = self.cache_dir / cache_key
        if cache_path.exists():
            logger.debug("LLM cache hit for model %s (key: %s)", self.model, cache_key[:8])
            return cache_path.read_text(encoding="utf-8")

        api_url = self._build_api_url()

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            if "azure.com" in self.base_url:
                headers["api-key"] = self.api_key
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

        logger.info(
            "Dispatching LLM completion to %s (model: %s, prompt_len: %d)",
            api_url,
            self.model,
            len(prompt),
        )
        try:
            response = httpx.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
            logger.info("Received LLM response for model %s (%d chars)", self.model, len(text))
        except Exception as exc:
            logger.error("LLM request failed for model %s at %s: %s", self.model, api_url, exc)
            raise

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(text, encoding="utf-8")
        return text
