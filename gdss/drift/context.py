"""Read-only lower-layer composition for deterministic branch collision analysis."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field

from gdss.conflict.tensor import ConflictTensor, TensorEngine, TensorEntry
from gdss.core import trajectory
from gdss.core.ast_parser import ASTParser
from gdss.core.transform_extractor import TransformExtractor
from gdss.core.transform_types import SemanticOperator
from gdss.drift.engine import DriftEngine
from gdss.watcher.git_observer import GitObserver


class AnalysisContextError(ValueError):
    """Raised when deterministic branch analysis cannot be constructed."""


@dataclass(frozen=True)
class AnalysisContext:
    """Reusable deterministic inputs for ranking, radar, and suggestion orchestration."""

    repo_path: str
    reference_branch: str
    active_branch: str
    branches: tuple[str, ...]
    branch_operators: Mapping[str, tuple[SemanticOperator, ...]]
    drift_magnitudes: Mapping[str, float]
    tensor: ConflictTensor
    observer: GitObserver
    parser: ASTParser
    extractor: TransformExtractor
    branch_commits: Mapping[str, tuple[dict[str, str], ...]] = field(default_factory=dict)
    branch_intents: Mapping[str, dict[str, str]] = field(default_factory=dict)


def _contact_keys(operator: SemanticOperator) -> tuple[str, ...]:
    names = tuple(
        name
        for name in (
            operator.name,
            operator.from_name,
            operator.to_name,
            operator.get_target_name(),
        )
        if name
    )
    if names:
        return tuple(f"{operator.file}\x1f{name}" for name in names)
    return (f"{operator.file}\x1f<file>",)


def iter_contact_pairs(
    context: AnalysisContext, entry: TensorEntry
) -> Iterator[tuple[SemanticOperator, SemanticOperator]]:
    """Yield indexed cross-branch operator contacts in O(j+i+c) time."""
    if entry.i == entry.j:
        return
    opposite: dict[str, list[SemanticOperator]] = defaultdict(list)
    for operator in context.branch_operators.get(entry.j, ()):
        for key in _contact_keys(operator):
            opposite[key].append(operator)

    yielded: set[tuple[int, int]] = set()
    for left in context.branch_operators.get(entry.i, ()):
        for key in _contact_keys(left):
            for right in opposite.get(key, ()):
                pair = (id(left), id(right))
                if pair not in yielded:
                    yielded.add(pair)
                    yield left, right


def build_analysis_context(
    repo_path: str,
    reference_branch: str,
    *,
    observer: GitObserver | None = None,
    parser: ASTParser | None = None,
    extractor: TransformExtractor | None = None,
    tensor_engine: TensorEngine | None = None,
    drift_engine: DriftEngine | None = None,
) -> AnalysisContext:
    """Build one deterministic, read-only branch analysis context.

    Drift magnitude calculation is intentionally used instead of snapshots so an
    analysis request does not append history or alter the target repository.
    """
    observer = observer or GitObserver(repo_path)
    if not observer.is_valid() or observer.repo is None:
        raise AnalysisContextError(
            "WHAT: repository is not a valid Git worktree.\n"
            "WHY: semantic trajectories require committed Git history.\n"
            "FIX: run gdss inside a local Git repository."
        )
    local_branches = observer.list_local_branches()
    branches = tuple(
        sorted(branch for branch in local_branches if branch != reference_branch)
    )
    if reference_branch not in local_branches:
        raise AnalysisContextError(
            f"WHAT: reference branch '{reference_branch}' is unavailable.\n"
            "WHY: branch trajectories must be measured from an existing attractor.\n"
            "FIX: pass --ref with a local branch name."
        )

    parser = parser or ASTParser()
    extractor = extractor or TransformExtractor()
    drift_engine = drift_engine or DriftEngine(observer, parser, extractor)
    branch_operators: dict[str, tuple[SemanticOperator, ...]] = {}
    drift_magnitudes: dict[str, float] = {}
    branch_commits: dict[str, tuple[dict[str, str], ...]] = {}
    for branch in branches:
        operators = trajectory.extract_trajectory_operators(
            observer,
            parser,
            extractor,
            ref_branch=reference_branch,
            head=branch,
        )
        branch_operators[branch] = tuple(operators)
        drift_magnitudes[branch] = drift_engine.compute_magnitude(
            branch, reference_branch
        ).magnitude
        branch_commits[branch] = tuple(observer.get_commits_between(reference_branch, branch))

    tensor = (tensor_engine or TensorEngine()).compute(
        {branch: list(operators) for branch, operators in branch_operators.items()},
        drift_magnitudes,
    )
    return AnalysisContext(
        repo_path=observer.repo_path,
        reference_branch=reference_branch,
        active_branch=observer.get_active_branch() or "DETACHED",
        branches=branches,
        branch_operators=branch_operators,
        drift_magnitudes=drift_magnitudes,
        tensor=tensor,
        observer=observer,
        parser=parser,
        extractor=extractor,
        branch_commits=branch_commits,
    )


def build_pr_analysis_context(
    repo_path: str,
    reference_branch: str,
    current_pr_branch: str,
    concurrent_branches: Sequence[str],
    *,
    pr_intents: Mapping[str, dict[str, str]] | None = None,
    observer: GitObserver | None = None,
    parser: ASTParser | None = None,
    extractor: TransformExtractor | None = None,
    tensor_engine: TensorEngine | None = None,
    drift_engine: DriftEngine | None = None,
) -> AnalysisContext:
    """Build deterministic AnalysisContext for an incoming PR against concurrent PR branches."""
    obs = observer or GitObserver(repo_path)
    if not obs.is_valid() or obs.repo is None:
        raise AnalysisContextError(
            "WHAT: repository is not a valid Git worktree.\n"
            "WHY: semantic trajectories require committed Git history.\n"
            "FIX: run gdss inside a local Git repository."
        )

    prs_to_track: list[str] = [current_pr_branch]
    for b in concurrent_branches:
        if b and b != reference_branch and b not in prs_to_track:
            prs_to_track.append(b)

    parser = parser or ASTParser()
    extractor = extractor or TransformExtractor()
    drift_engine = drift_engine or DriftEngine(obs, parser, extractor)
    branch_operators: dict[str, tuple[SemanticOperator, ...]] = {}
    drift_magnitudes: dict[str, float] = {}
    branch_commits: dict[str, tuple[dict[str, str], ...]] = {}

    for branch in prs_to_track:
        operators = trajectory.extract_trajectory_operators(
            obs,
            parser,
            extractor,
            ref_branch=reference_branch,
            head=branch,
        )
        branch_operators[branch] = tuple(operators)
        try:
            mag = drift_engine.compute_magnitude(branch, reference_branch).magnitude
        except Exception:
            mag = 0.5
        drift_magnitudes[branch] = mag
        branch_commits[branch] = tuple(obs.get_commits_between(reference_branch, branch))

    tensor = (tensor_engine or TensorEngine()).compute(
        {branch: list(operators) for branch, operators in branch_operators.items()},
        drift_magnitudes,
    )

    return AnalysisContext(
        repo_path=obs.repo_path,
        reference_branch=reference_branch,
        active_branch=current_pr_branch,
        branches=tuple(prs_to_track),
        branch_operators=branch_operators,
        drift_magnitudes=drift_magnitudes,
        tensor=tensor,
        observer=obs,
        parser=parser,
        extractor=extractor,
        branch_commits=branch_commits,
        branch_intents=dict(pr_intents or {}),
    )

