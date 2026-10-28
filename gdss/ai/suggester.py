"""Read-only orchestration for ranked, location-anchored AI suggestions."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Sequence
from dataclasses import replace

import httpx

from gdss.ai.anchors import resolve_anchor
from gdss.ai.conflict_topology import classify_conflict
from gdss.ai.context import AnalysisContext, build_analysis_context, iter_contact_pairs
from gdss.ai.llm_patch import AnyProvider, LLMProvider
from gdss.ai.ollama_provider import OllamaProvider
from gdss.ai.openai_provider import OpenAICompatibleProvider
from gdss.ai.patch_combinations import enumerate_combinations
from gdss.ai.prompt_builder import build_conflict_prompt
from gdss.ai.ranking import rank_tensor_entries
from gdss.ai.types import PatchCombination, Suggestion, SuggestionContext
from gdss.ai.validation import validate_patch
from gdss.ai.vllm_provider import VLLMProvider
from gdss.conflict.tensor import TensorEntry
from gdss.core.transform_types import SemanticOperator


def _operator_id(operator: SemanticOperator) -> str:
    payload = "\x1f".join(
        (
            operator.operator.value,
            operator.file,
            operator.symbol_id or "",
            operator.from_symbol_id or "",
            operator.to_symbol_id or "",
            operator.name or "",
            operator.from_name or "",
            operator.to_name or "",
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def _recommended_action(topology: str) -> str:
    return {
        "union": "review taking both compatible changes",
        "intersection": "reconcile the overlapping symbol changes",
        "disjoint": "choose an explicit resolution strategy",
        "asymmetric": "review both possible application orders",
    }[topology]


def _reason(
    entry: TensorEntry,
    left: SemanticOperator,
    right: SemanticOperator,
    topology: str,
) -> tuple[str, ...]:
    left_target = left.get_target_name() or left.file
    right_target = right.get_target_name() or right.file
    return (
        f"{entry.i} applies {left.operator.value} to {left_target}.",
        f"{entry.j} applies {right.operator.value} to {right_target}.",
        f"Pairwise omega is {entry.omega:.2f} ({', '.join(entry.reasons)}).",
        f"Conflict topology is {topology}.",
        f"Recommended action: {_recommended_action(topology)}.",
    )


def _anchored_block(context: AnalysisContext, suggestion: Suggestion) -> str:
    anchor = suggestion.anchor
    if anchor is None:
        return ""
    content = context.observer.get_file_content_at_commit(
        anchor.target_branch, anchor.file_path
    )
    if content is None:
        return ""
    return "".join(content.splitlines(keepends=True)[anchor.line_start - 1 : anchor.line_end])


def _draft_combinations(
    context: AnalysisContext,
    suggestion: Suggestion,
    provider: AnyProvider | LLMProvider,
) -> Suggestion:
    """Draft one patch per strategy and retain only deterministic validation passes."""
    from gdss.ai.context_builder import extract_3way_symbol_context

    model_name = getattr(provider, "model", None)
    other_branch = getattr(suggestion.context, "other_branch", None) if suggestion.context else None

    collision_ctx = extract_3way_symbol_context(
        context,
        suggestion,
        other_branch=other_branch,
        model_name=model_name,
        provider=provider,
    )
    block = collision_ctx.branch_a_code or _anchored_block(context, suggestion)

    num_combos = len(suggestion.patch_combinations)
    base_prompt = build_conflict_prompt(
        suggestion,
        block,
        context.repo_path,
        context.reference_branch,
        collision_context=collision_ctx,
        branch_commits=context.branch_commits,
        branch_intents=context.branch_intents,
        other_branch=other_branch,
    )
    drafted: list[PatchCombination] = []

    # Multi-strategy fast path: attempt single-roundtrip batch extraction if multiple strategies requested
    if num_combos > 1:
        labels = [c.label for c in suggestion.patch_combinations]
        batch_prompt = (
            base_prompt
            + "\nProduce candidate patches for all strategies:\n"
            + "\n".join(f"- {c.label}: {c.strategy}" for c in suggestion.patch_combinations)
            + "\nFormat each section as:\n--- patch: <file>:<start>-<end> (strategy: <label>) ---\n<diff>\n--- end ---"
        )
        try:
            from gdss.ai.patch_parser import parse_strategy_patches
            batch_text = provider.complete(batch_prompt)
            parsed = parse_strategy_patches(batch_text, expected_strategies=labels)
            for combination in suggestion.patch_combinations:
                patch_content = parsed.get(combination.label)
                if patch_content:
                    validation = validate_patch(suggestion, patch_content, original_code=block)
                    effective_patch = validation.synthesized_diff or patch_content
                    drafted.append(
                        replace(
                            combination,
                            patch_text=effective_patch if validation.valid else None,
                            source="llm",
                            validated=validation.valid,
                            validation_error=validation.reason,
                            validation_status="validated" if validation.valid else "rejected",
                        )
                    )
        except Exception:
            drafted = []

    # Strategy-by-strategy drafting fallback
    if len(drafted) != num_combos:
        drafted = []
        for combination in suggestion.patch_combinations:
            prompt = base_prompt + f"\nProduce only the `{combination.label}` strategy."
            patch_text = provider.complete(prompt)
            validation = validate_patch(suggestion, patch_text, original_code=block)
            effective_patch = validation.synthesized_diff or patch_text
            drafted.append(
                replace(
                    combination,
                    patch_text=effective_patch if validation.valid else None,
                    source="llm",
                    validated=validation.valid,
                    validation_error=validation.reason,
                    validation_status="validated" if validation.valid else "rejected",
                )
            )

    return replace(
        suggestion,
        patch_combinations=tuple(drafted),
        source="llm" if any(item.validated for item in drafted) else "deterministic",
        validated=all(item.validated for item in drafted) and bool(drafted),
    )


def _pick_provider(
    llm: bool,
    provider: AnyProvider | LLMProvider | None,
) -> AnyProvider | LLMProvider | None:
    """Return an LLM provider, preferring explicit, env credentials, or reachable local servers."""
    if provider is not None:
        return provider
    if not llm:
        return None
    if os.getenv("OPENROUTER_API_KEY") or os.getenv("GITHUB_TOKEN") or os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_BASE_URL"):
        return OpenAICompatibleProvider()
    if _server_reachable("http://localhost:8000"):
        return VLLMProvider()
    if _server_reachable("http://127.0.0.1:11434"):
        return OllamaProvider()
    return None


def _server_reachable(url: str) -> bool:
    try:
        httpx.get(url, timeout=3.0)
        return True
    except Exception:
        return False


def suggest(
    repo_path: str,
    reference_branch: str,
    *,
    branches: Sequence[str] | None = None,
    exclude_branches: Sequence[str] | None = None,
    llm: bool = False,
    combos: int = 3,
    provider: AnyProvider | LLMProvider | None = None,
    max_candidates: int = 50,
    context: AnalysisContext | None = None,
) -> list[Suggestion]:
    """Return ranked suggestions without applying patches or changing Git state."""
    if combos < 1 or max_candidates < 1:
        raise ValueError("combos and max_candidates must both be positive")
    ctx = context or build_analysis_context(
        repo_path,
        reference_branch,
        branches=branches,
        exclude_branches=exclude_branches,
    )
    ranked = rank_tensor_entries(
        ctx.tensor, drift_magnitudes=ctx.drift_magnitudes
    )
    suggestions: list[Suggestion] = []
    seen: set[tuple[str, str, str, str]] = set()
    draft_provider = _pick_provider(llm, provider)

    for candidate in ranked:
        entry = candidate.entry
        if entry.i == entry.j:
            continue
        for left, right in iter_contact_pairs(ctx, entry):
            left_id = _operator_id(left)
            right_id = _operator_id(right)
            key = (entry.i, entry.j, left_id, right_id)
            if key in seen:
                continue
            seen.add(key)
            anchor = resolve_anchor(
                ctx.observer, ctx.parser, left, entry.i
            )
            if anchor is None:
                continue
            topology = classify_conflict(
                left,
                right,
                symbol_overlap=None,
                symbol_id=left.symbol_id or anchor.symbol_digest,
            )
            suggestion = Suggestion(
                kind=left.operator.value,
                file_path=anchor.file_path,
                line_start=anchor.line_start,
                line_end=anchor.line_end,
                symbol_id=left.symbol_id or anchor.symbol_digest,
                operator=left.operator.value,
                action=_recommended_action(topology.kind),
                rationale=topology.justification,
                reason=_reason(entry, left, right, topology.kind),
                confidence=candidate.confidence,
                rank=len(suggestions) + 1,  # dsa:ignore
                topology=topology,
                patch_combinations=tuple(enumerate_combinations(topology)[:combos]),
                anchor=anchor,
                context=SuggestionContext(
                    reference_branch=ctx.reference_branch,
                    candidate_branch=entry.i,
                    omega=entry.omega,
                    merge_risk=ctx.tensor.merge_risk,
                    operator_i_id=left_id,
                    operator_j_id=right_id,
                    other_branch=entry.j,
                ),
            )
            if draft_provider is not None:
                suggestion = _draft_combinations(ctx, suggestion, draft_provider)
            suggestions.append(suggestion)
            if len(suggestions) >= max_candidates:  # dsa:ignore
                return suggestions
    return suggestions
