"""AST-aware context condensation for massively large semantic blocks with 3-tier context discovery."""

from __future__ import annotations

import os
from typing import Any

from gdss.ai.context import AnalysisContext
from gdss.ai.types import Suggestion

_METADATA_CACHE: dict[str, int] = {}


def resolve_context_window(
    model_name: str | None,
    provider: Any | None = None,
    user_override: int | None = None,
) -> int:
    """Resolve model context window using 3-tier discovery:
    1. Explicit user override (from .gdss.yml, CLI argument, or GDSS_CONTEXT_WINDOW).
    2. Dynamic Provider API inspection (OpenRouter, Ollama, vLLM).
    3. Resilient family pattern heuristics with a safe 16k fallback.
    """
    # Tier 1: User / Environment Override
    if user_override is not None and user_override > 0:
        return user_override

    env_val = os.getenv("GDSS_CONTEXT_WINDOW")
    if env_val and env_val.isdigit():
        return int(env_val)

    normalized_model = model_name.strip() if isinstance(model_name, str) else ""
    if normalized_model and normalized_model in _METADATA_CACHE:
        return _METADATA_CACHE[normalized_model]

    # Tier 2: Dynamic Provider Metadata Inspection
    if provider is not None and normalized_model:
        try:
            import httpx

            # OpenRouter Models API
            base_url = str(getattr(provider, "base_url", "") or "")
            if "openrouter.ai" in base_url:
                openrouter_resp = httpx.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={"Authorization": f"Bearer {getattr(provider, 'api_key', '')}"},
                    timeout=5.0,
                )
                if openrouter_resp.status_code == 200:
                    openrouter_data = openrouter_resp.json().get("data", [])  # dsa:ignore
                    for item in openrouter_data:
                        if item.get("id") == normalized_model:
                            ctx_len = int(item.get("context_length", 0))
                            if ctx_len > 0:
                                _METADATA_CACHE[normalized_model] = ctx_len
                                return ctx_len

            provider_cls_name = provider.__class__.__name__ if provider is not None else ""

            # Ollama /api/show API
            host = str(getattr(provider, "host", "") or "")
            if "11434" in host or provider_cls_name == "OllamaProvider":
                ollama_url = f"{host.rstrip('/')}/api/show" if host else "http://localhost:11434/api/show"
                ollama_resp = httpx.post(ollama_url, json={"name": normalized_model}, timeout=3.0)
                if ollama_resp.status_code == 200:
                    ollama_info = ollama_resp.json().get("model_info", {})  # dsa:ignore
                    for k, v in ollama_info.items():
                        if "context_length" in k and isinstance(v, (int, float)) and v > 0:
                            ctx_len = int(v)
                            _METADATA_CACHE[normalized_model] = ctx_len
                            return ctx_len

            # vLLM /v1/models API
            if "8000" in base_url or provider_cls_name == "VLLMProvider":
                vllm_url = f"{base_url.rstrip('/')}/models" if base_url else "http://localhost:8000/v1/models"
                vllm_resp = httpx.get(vllm_url, timeout=3.0)
                if vllm_resp.status_code == 200:
                    vllm_data = vllm_resp.json().get("data", [])  # dsa:ignore
                    for item in vllm_data:
                        if item.get("id") == normalized_model:
                            max_len = int(item.get("max_model_len", 0))
                            if max_len > 0:
                                _METADATA_CACHE[normalized_model] = max_len
                                return max_len
        except Exception:
            pass

    # Tier 3: Resilient Family Pattern Heuristics
    m = normalized_model.lower()
    if any(p in m for p in ("gpt-4o", "o1", "o3", "chatgpt-4o")):
        ctx = 128000
    elif any(p in m for p in ("claude-3", "claude-3-5")):
        ctx = 200000
    elif "llama-3.1" in m or "llama-3.2" in m:
        ctx = 128000
    elif "deepseek" in m:
        ctx = 64000
    elif "qwen2.5" in m:
        ctx = 32768
    elif "llama-3" in m:
        ctx = 8192
    else:
        ctx = 16384

    if normalized_model:
        _METADATA_CACHE[normalized_model] = ctx
    return ctx


def get_model_code_budget(
    model_name: str | None,
    provider: Any | None = None,
    user_override: int | None = None,
) -> int:
    """Return character budget for code blocks based on resolved context window.

    Reserves ~9,000 tokens for system prompt, developer intent, commit messages, and output.
    Uses ~3.5 characters per token.
    """
    tokens = resolve_context_window(model_name, provider=provider, user_override=user_override)
    available_tokens = max(tokens - 9000, min(tokens // 2, 4000))
    return int(available_tokens * 3.5)


def condense_block(
    context: AnalysisContext,
    suggestion: Suggestion,
    original_block: str,
    max_chars: int | None = None,
) -> str:
    """Condense the block by omitting unmodified methods to fit model context budget."""
    budget = max_chars if max_chars is not None and max_chars > 0 else 24000
    if len(original_block) <= budget:
        return original_block

    anchor = suggestion.anchor
    if not anchor:
        return original_block

    full_content = context.observer.get_file_content_at_commit(context.reference_branch, anchor.file_path)
    if not full_content:
        return original_block

    symbols = context.parser.parse_file(anchor.file_path, full_content)

    # Identify which symbols are being modified in this conflict
    modified_names: set[str] = set()
    for branch_ops in context.branch_operators.values():
        for op in branch_ops:
            if op.file == anchor.file_path:
                if op.name:
                    modified_names.add(op.name)
                if op.to_name:
                    modified_names.add(op.to_name)
                if op.from_name:
                    modified_names.add(op.from_name)
                target = op.get_target_name()
                if target:
                    modified_names.add(target)

    anchor_lines = original_block.splitlines(keepends=True)

    # Find child symbols entirely inside the anchor that are NOT modified
    children = [
        s for s in symbols
        if s.start_line > anchor.line_start and s.end_line <= anchor.line_end
        and s.name not in modified_names
    ]

    # Process from bottom to top to avoid shifting line indices
    children.sort(key=lambda s: s.start_line, reverse=True)

    for child in children:
        rel_start = child.start_line - anchor.line_start
        rel_end = child.end_line - anchor.line_start + 1

        if rel_end - rel_start > 2:
            try:
                indent = len(anchor_lines[rel_start]) - len(anchor_lines[rel_start].lstrip())
                omission = (" " * indent) + "    # ... (unmodified code omitted) ...\n"
                anchor_lines[rel_start + 1 : rel_end] = [omission]
            except IndexError:
                continue

    condensed = "".join(anchor_lines)

    # If it still exceeds budget, do a balanced head/tail crop
    if len(condensed) > budget:
        lines = condensed.splitlines(keepends=True)
        if len(lines) > 200:
            condensed = "".join(lines[:100]) + "\n# ... (hard omitted) ...\n" + "".join(lines[-100:])

    return condensed

