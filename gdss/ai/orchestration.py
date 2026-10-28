"""Agent orchestration pipeline for analysis, drafting, validation, and audited suggestion state.

Coordinates the convergence lifecycle:
1. Deterministic Analysis & Ranking (Tensor, topology, anchors)
2. Optional Drafting (Model-free templates or local/external LLM)
3. Ephemeral Sandbox Validation (Worktree syntax, types, and tests)
4. Audited Suggestion State Caching (.gdss/suggestions/sug_... metadata)
5. Awaiting Human Review Checkpoint (Strictly pauses for human approval; never auto-merges)

Pure-Python state machine by default; optionally exports to LangGraph if installed.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

from gdss.ai.context import AnalysisContext, build_analysis_context
from gdss.ai.llm_patch import AnyProvider, LLMProvider
from gdss.ai.suggester import _draft_combinations, _pick_provider, suggest
from gdss.ai.suggestion_store import save_suggestion
from gdss.ai.types import PatchCombination, Suggestion
from gdss.logger import get_logger
from gdss.watcher.git_observer import GitObserver

logger = get_logger("gdss.ai.orchestration")

CheckpointStatus = Literal[
    "init",
    "analyzed",
    "drafted",
    "validated",
    "refined",
    "awaiting_human_review",
    "failed",
]


@dataclass
class ConvergenceState:
    """State passed across the convergence orchestration lifecycle."""

    repo_path: str
    reference_branch: str = "main"
    llm: bool = False
    validate: bool = False
    combos: int = 3
    max_candidates: int = 50
    sandbox_timeout: float | None = None
    provider: AnyProvider | LLMProvider | None = None
    target_commit: str = ""
    validator: Callable[[str, str, float | None], tuple[bool, str | None]] | None = None
    suggestions: list[Suggestion] = field(default_factory=list)
    checkpoint: CheckpointStatus = "init"
    errors: list[str] = field(default_factory=list)
    analysis_context: AnalysisContext | None = None
    branches: list[str] | None = None
    exclude_branches: list[str] | None = None
    max_refinements: int = 2
    refinement_count: int = 0
    refinement_history: list[dict[str, Any]] = field(default_factory=list)


def _coerce_state(state: Any) -> ConvergenceState:
    if isinstance(state, ConvergenceState):
        return state
    if isinstance(state, dict):
        return ConvergenceState(**state)
    return state


def analyze_step(state: ConvergenceState) -> ConvergenceState:
    """Deterministic step: compute conflict topology, anchors, and rankings."""
    st = _coerce_state(state)
    logger.info("Orchestration [Node: analyze]: computing topology and anchors on %s", st.repo_path)
    if not st.target_commit:
        try:
            observer = GitObserver(st.repo_path)
            if observer.repo:
                st.target_commit = observer.repo.head.commit.hexsha
            else:
                st.target_commit = "HEAD"
        except Exception:
            st.target_commit = "HEAD"

    if st.suggestions:
        logger.debug("Existing %d suggestion(s) provided, skipping suggestion generation", len(st.suggestions))
        st.checkpoint = "analyzed"
        return st

    try:
        suggestions = suggest(
            st.repo_path,
            st.reference_branch,
            branches=st.branches,
            exclude_branches=st.exclude_branches,
            llm=False,
            combos=st.combos,
            max_candidates=st.max_candidates,
            context=st.analysis_context,
        )
        st.suggestions = list(suggestions)
        logger.info("Orchestration [Node: analyze]: identified %d candidate suggestions", len(st.suggestions))  # dsa:ignore
        st.checkpoint = "analyzed"
    except Exception as exc:
        logger.error("Analysis step failed: %s", exc, exc_info=True)
        st.errors.append(f"Analysis step failed: {exc}")
        st.checkpoint = "failed"

    return st


def draft_step(state: ConvergenceState) -> ConvergenceState:
    """Drafting step: model-free deterministic templates or optional LLM provider."""
    st = _coerce_state(state)
    if st.checkpoint == "failed":
        return st

    sug_count = len(st.suggestions)
    if not st.llm or not st.suggestions:
        logger.debug("Orchestration [Node: draft]: skipping LLM drafting (llm=%s, count=%d)", st.llm, sug_count)
        st.checkpoint = "drafted"
        return st

    logger.info("Orchestration [Node: draft]: drafting patches for %d suggestions via LLM", sug_count)
    try:
        active_provider = _pick_provider(True, st.provider)
        if active_provider is not None:
            context = st.analysis_context or build_analysis_context(st.repo_path, st.reference_branch)
            drafted: list[Suggestion] = []
            for item in st.suggestions:
                drafted.append(_draft_combinations(context, item, active_provider))
            st.suggestions = drafted
            logger.info("Orchestration [Node: draft]: completed drafting for %d suggestions", len(drafted))
        st.checkpoint = "drafted"
    except Exception as exc:
        logger.error("Drafting step failed: %s", exc, exc_info=True)
        st.errors.append(f"Drafting step failed: {exc}")
        st.checkpoint = "drafted"

    return st


def validate_step(state: ConvergenceState) -> ConvergenceState:
    """Validation step: test candidate patches in ephemeral Git worktree sandbox."""
    st = _coerce_state(state)
    if st.checkpoint == "failed":
        return st

    sug_count = len(st.suggestions)
    if not st.validate or not st.suggestions:
        logger.debug("Orchestration [Node: validate]: skipping validation (validate=%s, count=%d)", st.validate, sug_count)
        st.checkpoint = "validated"
        return st

    logger.info("Orchestration [Node: validate]: validating %d suggestion(s) in sandbox", sug_count)
    try:
        validator = st.validator
        if validator is None:
            import importlib
            mod = importlib.import_module("gdss.validation.sandbox")
            sandbox_cls = mod.ValidationSandbox
            sandbox = sandbox_cls(st.repo_path)

            def _sandbox_run(patch: str, target: str, timeout: float | None) -> tuple[bool, str | None]:
                rep = sandbox.validate_patch(patch, target_branch=target, timeout_seconds=timeout)
                return bool(rep.is_clean), rep.error_summary

            validator = _sandbox_run

        validated_list: list[Suggestion] = []
        for sug in st.suggestions:
            updated_combos: list[PatchCombination] = []
            for combo in sug.patch_combinations:
                if combo.patch_text:
                    is_valid, err_msg = validator(
                        combo.patch_text,
                        st.target_commit or "HEAD",
                        st.sandbox_timeout,
                    )
                    status_str: Literal["validated", "rejected"] = (
                        "validated" if is_valid else "rejected"
                    )
                    logger.debug(
                        "Validation result for %s (strategy: %s): %s",
                        sug.suggestion_id,
                        combo.label,
                        status_str,
                    )
                    updated_combos.append(
                        replace(
                            combo,
                            validated=is_valid,
                            validation_status=status_str,
                            validation_error=err_msg if not is_valid else None,
                        )
                    )
                else:
                    updated_combos.append(combo)

            validated_sug = replace(
                sug,
                patch_combinations=tuple(updated_combos),
                validated=any(c.validated for c in updated_combos),
            )
            validated_list.append(validated_sug)

        st.suggestions = validated_list
        valid_count = sum(1 for s in st.suggestions if s.validated)
        logger.info("Orchestration [Node: validate]: %d/%d suggestions passed validation", valid_count, len(validated_list))
        st.checkpoint = "validated"
    except Exception as exc:
        logger.error("Validation step failed: %s", exc, exc_info=True)
        st.errors.append(f"Validation step failed: {exc}")
        st.checkpoint = "validated"

    return st


def should_refine(state: ConvergenceState) -> str:
    """Decide whether to transition to refine or checkpoint."""
    st = _coerce_state(state)
    if st.checkpoint == "failed":
        return "checkpoint"
    if not st.llm or not st.validate or not st.provider:
        return "checkpoint"
    if st.refinement_count >= st.max_refinements:
        logger.debug("Reached max refinements (%d), transitioning to checkpoint", st.max_refinements)
        return "checkpoint"

    needs_refinement = any(
        (not combo.validated) and bool(combo.patch_text) and bool(combo.validation_error)
        for sug in st.suggestions
        for combo in sug.patch_combinations
    )
    if needs_refinement:
        logger.info(
            "Strategies requiring refinement detected. Entering refinement iteration %d/%d",
            st.refinement_count + 1,
            st.max_refinements,
        )
        return "refine"
    return "checkpoint"


def refine_step(state: ConvergenceState) -> ConvergenceState:
    """Refinement step: re-prompt LLM with compiler/test failure traces to self-correct."""
    st = _coerce_state(state)
    if st.checkpoint == "failed" or not st.provider:
        return st

    logger.info("Orchestration [Node: refine]: executing self-correction attempt %d", st.refinement_count + 1)
    from gdss.ai.prompt_builder import build_refinement_prompt
    from gdss.ai.suggester import _anchored_block
    from gdss.ai.validation import validate_patch

    context = st.analysis_context
    if context is None:
        try:
            context = build_analysis_context(st.repo_path, st.reference_branch)
        except Exception:
            context = None

    active_provider = _pick_provider(True, st.provider)
    if active_provider is None:
        return st

    refined_suggestions: list[Suggestion] = []
    for sug in st.suggestions:
        updated_combos: list[PatchCombination] = []
        for combo in sug.patch_combinations:
            if not combo.validated and combo.patch_text and combo.validation_error:
                from gdss.ai.context_builder import extract_3way_symbol_context
                from gdss.ai.patch_parser import extract_patch_or_replacement

                other_branch = getattr(sug.context, "other_branch", None) if sug.context else None
                collision_ctx = extract_3way_symbol_context(context, sug, other_branch=other_branch) if context else None
                block = (collision_ctx.branch_a_code if collision_ctx else None) or (_anchored_block(context, sug) if context else "")
                branch_commits = context.branch_commits if context else None
                branch_intents = context.branch_intents if context else None

                prompt = build_refinement_prompt(
                    suggestion=sug,
                    strategy_label=combo.label,
                    previous_patch=combo.patch_text,
                    validation_error=combo.validation_error,
                    repo=st.repo_path,
                    ref=st.reference_branch,
                    anchored_symbol_block=block,
                    collision_context=collision_ctx,
                    branch_commits=branch_commits,
                    branch_intents=branch_intents,
                    other_branch=other_branch,
                )
                try:
                    raw_resp = active_provider.complete(prompt).strip()
                    refined_text, _ = extract_patch_or_replacement(raw_resp, expected_file=sug.file_path)

                    validation = validate_patch(sug, refined_text, original_code=block)
                    effective_patch = validation.synthesized_diff or refined_text
                    st.refinement_history.append(
                        {
                            "suggestion_id": sug.suggestion_id,
                            "strategy": combo.label,
                            "attempt": st.refinement_count + 1,
                            "previous_error": combo.validation_error,
                        }
                    )
                    updated_combos.append(
                        replace(
                            combo,
                            patch_text=effective_patch if validation.valid else combo.patch_text,
                            validated=False,
                            validation_status="draft",
                            validation_error=validation.reason if not validation.valid else None,
                        )
                    )
                except Exception as exc:
                    st.errors.append(f"Refinement error for {sug.suggestion_id} ({combo.label}): {exc}")
                    updated_combos.append(combo)
            else:
                updated_combos.append(combo)

        refined_suggestions.append(replace(sug, patch_combinations=tuple(updated_combos)))

    st.suggestions = refined_suggestions
    st.refinement_count += 1
    st.checkpoint = "refined"
    return st


def checkpoint_step(state: ConvergenceState) -> ConvergenceState:
    """Audit step: assign IDs, cache metadata in .gdss/suggestions/, pause for human review."""
    st = _coerce_state(state)
    if st.checkpoint == "failed":
        return st

    logger.info("Orchestration [Node: audit]: caching %d suggestion(s) to suggestion store", len(st.suggestions))
    try:
        for sug in st.suggestions:
            save_suggestion(
                sug,
                repo_root=st.repo_path,
                target_commit=st.target_commit,
            )
        st.checkpoint = "awaiting_human_review"
    except Exception as exc:
        logger.error("Checkpoint step failed: %s", exc, exc_info=True)
        st.errors.append(f"Checkpoint step failed: {exc}")
        st.checkpoint = "awaiting_human_review"

    return st


class OrchestrationPipeline:
    """Sequential runner executing the convergence orchestration lifecycle."""

    def __init__(
        self,
        repo_path: str | Path,
        reference_branch: str = "main",
        *,
        llm: bool = False,
        validate: bool = False,
        combos: int = 3,
        max_candidates: int = 50,
        sandbox_timeout: float | None = None,
        provider: AnyProvider | LLMProvider | None = None,
        target_commit: str = "",
        validator: Callable[[str, str, float | None], tuple[bool, str | None]] | None = None,
        analysis_context: AnalysisContext | None = None,
        max_refinements: int = 2,
        suggestions: list[Suggestion] | None = None,
    ) -> None:
        self.state = ConvergenceState(
            repo_path=str(repo_path),
            reference_branch=reference_branch,
            llm=llm,
            validate=validate,
            combos=combos,
            max_candidates=max_candidates,
            sandbox_timeout=sandbox_timeout,
            provider=provider,
            target_commit=target_commit,
            validator=validator,
            analysis_context=analysis_context,
            max_refinements=max_refinements,
            suggestions=list(suggestions or []),
        )

    def run(self) -> ConvergenceState:
        """Execute the full pipeline through to awaiting_human_review with refinement loop."""
        state = analyze_step(self.state)
        state = draft_step(state)
        while True:
            state = validate_step(state)
            if should_refine(state) == "refine":
                state = refine_step(state)
            else:
                break
        state = checkpoint_step(state)
        return state


def build_langgraph_workflow() -> Any:
    """Construct an optional LangGraph workflow if langgraph is installed in the environment."""
    try:
        from langgraph.graph import END, StateGraph
    except ImportError as exc:
        raise ImportError(
            "LangGraph is an optional dependency. Install with 'pip install langgraph' to use LangGraph graph export."
        ) from exc

    workflow = StateGraph(ConvergenceState)
    workflow.add_node("analyze", analyze_step)
    workflow.add_node("draft", draft_step)
    workflow.add_node("validate", validate_step)
    workflow.add_node("refine", refine_step)
    workflow.add_node("checkpoint", checkpoint_step)

    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "draft")
    workflow.add_edge("draft", "validate")
    workflow.add_conditional_edges(
        "validate",
        should_refine,
        {
            "refine": "refine",
            "checkpoint": "checkpoint",
        },
    )
    workflow.add_edge("refine", "validate")
    workflow.add_edge("checkpoint", END)

    return workflow.compile()


def run_convergence_pipeline(
    state: ConvergenceState,
    *,
    use_langgraph: bool = True,
) -> ConvergenceState:
    """Execute convergence pipeline, preferring LangGraph if available, with pure-Python fallback."""
    if use_langgraph:
        try:
            workflow = build_langgraph_workflow()
            result = workflow.invoke(state)
            if isinstance(result, ConvergenceState):
                return result
            if isinstance(result, dict):
                for k, v in result.items():
                    if hasattr(state, k):
                        setattr(state, k, v)
                return state
        except Exception:
            pass

    pipeline = OrchestrationPipeline(
        repo_path=state.repo_path,
        reference_branch=state.reference_branch,
        llm=state.llm,
        validate=state.validate,
        combos=state.combos,
        max_candidates=state.max_candidates,
        sandbox_timeout=state.sandbox_timeout,
        provider=state.provider,
        target_commit=state.target_commit,
        validator=state.validator,
        analysis_context=state.analysis_context,
        max_refinements=state.max_refinements,
        suggestions=state.suggestions,
    )
    pipeline.state = state
    return pipeline.run()

