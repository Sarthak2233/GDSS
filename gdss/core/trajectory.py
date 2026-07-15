"""Deterministic trajectory operators: merge_base(ref, HEAD)..HEAD."""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from gdss.core.ast_parser import ASTParser, SOURCE_EXTENSIONS
from gdss.core.transform_extractor import TransformExtractor
from gdss.core.transform_types import SemanticOperator
from gdss.watcher.git_observer import GitObserver


def extract_trajectory_operators(
    observer: GitObserver,
    parser: ASTParser,
    extractor: TransformExtractor,
    ref_branch: str,
    head: str = "HEAD",
    extensions: Sequence[str] = SOURCE_EXTENSIONS,
) -> List[SemanticOperator]:
    """
    Aggregate symbol-level SemanticOperators across committed divergence
    from the reference attractor to the tip of ``head``.

    Empty when tip equals reference (or merge-base is the tip).
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
    operators: List[SemanticOperator] = []
    ext_tuple = tuple(extensions)

    for path in changes.get("modified", []):
        if not path.endswith(ext_tuple):
            continue
        old_content = observer.get_file_content_at_commit(merge_base, path)  # dsa:ignore
        new_content = observer.get_file_content_at_commit(head_commit.hexsha, path)  # dsa:ignore
        if old_content is None or new_content is None:
            continue
        old_syms = parser.parse_file(path, old_content)  # dsa:ignore
        new_syms = parser.parse_file(path, new_content)  # dsa:ignore
        operators.extend(
            extractor.extract_operators(path, old_syms, new_syms, commit_sha=head_commit.hexsha)
        )

    for path in changes.get("added", []):
        if not path.endswith(ext_tuple):
            continue
        new_content = observer.get_file_content_at_commit(head_commit.hexsha, path)  # dsa:ignore
        if new_content is None:
            continue
        new_syms = parser.parse_file(path, new_content)  # dsa:ignore
        operators.extend(
            extractor.extract_operators(path, [], new_syms, commit_sha=head_commit.hexsha)
        )

    for path in changes.get("deleted", []):
        if not path.endswith(ext_tuple):
            continue
        old_content = observer.get_file_content_at_commit(merge_base, path)  # dsa:ignore
        if old_content is None:
            continue
        old_syms = parser.parse_file(path, old_content)  # dsa:ignore
        operators.extend(
            extractor.extract_operators(path, old_syms, [], commit_sha=head_commit.hexsha)
        )

    return operators


def is_single_attractor_trajectory(
    observer: GitObserver, reference_branch: str
) -> Tuple[bool, Optional[str]]:
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
