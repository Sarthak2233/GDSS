"""Topological conflict partitioning for parallel AI convergence orchestration.

Groups candidate conflict suggestions into independent vs file-coupled clusters,
enabling parallel concurrent drafting without cross-file race conditions or
context fragmentation.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from collections.abc import Sequence
from dataclasses import dataclass

from gdss.ai.types import Suggestion
from gdss.logger import get_logger

logger = get_logger("gdss.ai.partitioner")


@dataclass(frozen=True)
class ConflictCluster:
    """A cluster of suggestions that share file or symbol coupling."""

    cluster_id: str
    file_path: str
    suggestions: tuple[Suggestion, ...]
    is_independent: bool


def partition_conflicts(suggestions: Sequence[Suggestion]) -> list[ConflictCluster]:
    """Group suggestions into file-coupled vs independent clusters.

    Suggestions affecting the same file are grouped into a single cluster so that
    the AI provider maintains full contextual visibility across all symbol changes
    in that file. Disjoint files are isolated into independent clusters that can
    execute concurrently in parallel.
    """
    if not suggestions:
        return []

    # Preserve deterministic encounter order by file path
    groups: OrderedDict[str, list[Suggestion]] = OrderedDict()
    for sug in suggestions:
        fpath = sug.file_path or (sug.anchor.file_path if sug.anchor else "unknown")
        if fpath not in groups:
            groups[fpath] = []
        groups[fpath].append(sug)

    clusters: list[ConflictCluster] = []
    for idx, (fpath, sug_list) in enumerate(groups.items(), start=1):
        digest = hashlib.sha256(fpath.encode("utf-8")).hexdigest()[:8]
        cluster_id = f"cluster_{idx}_{digest}"
        is_independent = len(groups) > 1 or len(sug_list) == 1
        clusters.append(
            ConflictCluster(
                cluster_id=cluster_id,
                file_path=fpath,
                suggestions=tuple(sug_list),
                is_independent=is_independent,
            )
        )

    logger.debug(
        "Partitioned %d suggestion(s) into %d conflict cluster(s)",
        len(suggestions),
        len(clusters),
    )
    return clusters

