"""Deterministic trajectory operators: merge_base(ref, HEAD)..HEAD."""

from __future__ import annotations

from collections.abc import Sequence

from gdss.core.ast_parser import SOURCE_EXTENSIONS, ASTParser
from gdss.core.transform_extractor import TransformExtractor
from gdss.core.transform_types import SemanticOperator
from gdss.reducers.registry import DomainReducerRegistry
from gdss.watcher.git_observer import GitObserver


def extract_trajectory_operators(
    observer: GitObserver,
    parser: ASTParser,
    extractor: TransformExtractor,
    ref_branch: str,
    head: str = "HEAD",
    extensions: Sequence[str] = SOURCE_EXTENSIONS,
    reducer_registry: DomainReducerRegistry | None = None,
) -> list[SemanticOperator]:
    """
    Aggregate symbol-level SemanticOperators across committed divergence
    from the reference attractor to the tip of ``head``.

    Evaluates both Code AST symbols and Domain Reducers (manifests, migrations, SQL,
    markdown, lexical chunks). Empty when tip equals reference (or merge-base is the tip).
    """
    if not observer.is_valid() or observer.repo is None:
        return []

    try:
        head_commit = observer.repo.commit(head)
        ref_commit = observer.repo.commit(ref_branch)
    except Exception:
        return []

    if head_commit.hexsha == ref_commit.hexsha:
        return []

    merge_base = observer.get_merge_base(head, ref_branch)
    if not merge_base or merge_base == head_commit.hexsha:
        return []

    changes = observer.get_file_diffs_between_commits(merge_base, head_commit.hexsha)
    operators: list[SemanticOperator] = []
    ext_tuple = tuple(extensions)
    registry = reducer_registry or DomainReducerRegistry()

    for path in changes.get("modified", []):
        old_content = observer.get_file_content_at_commit(merge_base, path)  # dsa:ignore
        new_content = observer.get_file_content_at_commit(head_commit.hexsha, path)  # dsa:ignore
        if old_content is None and new_content is None:
            continue
        domain_reducer = registry.get_reducer(path, content=new_content or old_content)
        if domain_reducer is not None:
            operators.extend(
                domain_reducer.extract_operators(
                    path, old_content, new_content, commit_sha=head_commit.hexsha
                )
            )
        elif path.endswith(ext_tuple):
            old_syms = parser.parse_file(path, old_content) if old_content else []  # dsa:ignore
            new_syms = parser.parse_file(path, new_content) if new_content else []  # dsa:ignore
            operators.extend(
                extractor.extract_operators(path, old_syms, new_syms, commit_sha=head_commit.hexsha)
            )

    for path in changes.get("added", []):
        new_content = observer.get_file_content_at_commit(head_commit.hexsha, path)  # dsa:ignore
        if new_content is None:
            continue
        domain_reducer = registry.get_reducer(path, content=new_content)
        if domain_reducer is not None:
            operators.extend(
                domain_reducer.extract_operators(
                    path, None, new_content, commit_sha=head_commit.hexsha
                )
            )
        elif path.endswith(ext_tuple):
            new_syms = parser.parse_file(path, new_content)  # dsa:ignore
            operators.extend(
                extractor.extract_operators(path, [], new_syms, commit_sha=head_commit.hexsha)
            )

    for path in changes.get("deleted", []):
        old_content = observer.get_file_content_at_commit(merge_base, path)  # dsa:ignore
        if old_content is None:
            continue
        domain_reducer = registry.get_reducer(path, content=old_content)
        if domain_reducer is not None:
            operators.extend(
                domain_reducer.extract_operators(
                    path, old_content, None, commit_sha=head_commit.hexsha
                )
            )
        elif path.endswith(ext_tuple):
            old_syms = parser.parse_file(path, old_content)  # dsa:ignore
            operators.extend(
                extractor.extract_operators(path, old_syms, [], commit_sha=head_commit.hexsha)
            )

    return operators


def is_single_attractor_trajectory(
    observer: GitObserver, reference_branch: str
) -> tuple[bool, str | None]:
    """
    True when only one local branch exists and its tip equals the reference tip.
    """
    if not observer.is_valid() or observer.repo is None:
        return False, None
    branches = observer.list_local_branches()
    if len(branches) != 1:
        return False, None
    only = branches[0]
    try:
        tip = observer.repo.commit(only).hexsha
        ref_tip = observer.repo.commit(reference_branch).hexsha
    except Exception:
        return False, only
    return tip == ref_tip, only
