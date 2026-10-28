from __future__ import annotations

import fnmatch
import json
from collections.abc import Sequence
from typing import Any

from gdss.logger import get_logger
from gdss.storage.db import RuntimeDB

logger = get_logger("gdss.runtime.hierarchy")


def matches_any_pattern(name: str, patterns: Sequence[str]) -> bool:
    """Return True if name matches any pattern (exact or fnmatch wildcard)."""
    return any(fnmatch.fnmatch(name, pat) for pat in patterns)


def filter_branches(
    branches: Sequence[str],
    include: Sequence[str] | None = None,
    exclude: Sequence[str] | None = None,
    reference_branch: str | None = None,
) -> list[str]:
    """
    Filter branch list by include/exclude patterns and exclude reference branch.

    Rules:
    1. If reference_branch is provided, it is excluded (attractor is reference, not candidate).
    2. If include is provided and non-empty, only branches matching at least one pattern are kept.
    3. If exclude is provided and non-empty, any branch matching any exclude pattern is omitted.
    4. Deterministic order of input branches is preserved.
    """
    include_patterns = [p for p in include if p] if include else []
    exclude_patterns = [p for p in exclude if p] if exclude else []

    result: list[str] = []
    for branch in branches:
        if reference_branch and branch == reference_branch:
            continue
        if include_patterns and not matches_any_pattern(branch, include_patterns):
            continue
        if exclude_patterns and matches_any_pattern(branch, exclude_patterns):
            continue
        result.append(branch)
    return result


class HierarchyManager:
    """
    Layer 3: Distributed Hierarchy Manager.
    Resolves branch priorities, filters, and development trajectories.
    """

    def __init__(self, db: RuntimeDB):
        self.db = db

    def set_config(self, repo_id: int, config: dict[str, Any]):
        """Persist or update hierarchy configuration for a repository."""
        payload = json.dumps(config)
        with self.db._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE hierarchies SET config_payload = ? WHERE repo_id = ?",
                (payload, repo_id),
            )
            if cursor.rowcount == 0:
                conn.execute(
                    "INSERT INTO hierarchies (repo_id, config_payload) VALUES (?, ?)",
                    (repo_id, payload),
                )
        logger.debug("Updated hierarchy config for repo_id %s", repo_id)

    def get_config(self, repo_id: int) -> dict[str, Any]:
        """Fetch hierarchy configuration for a repository."""
        with self.db._get_connection() as conn:
            cursor = conn.execute(
                "SELECT config_payload FROM hierarchies WHERE repo_id = ? ORDER BY id DESC LIMIT 1",
                (repo_id,),
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row["config_payload"])
            return {}

    def set_branch_filters(
        self,
        repo_id: int,
        include: Sequence[str] | None = None,
        exclude: Sequence[str] | None = None,
    ) -> None:
        """Persist include/exclude branch pattern filters for a repository."""
        config = self.get_config(repo_id)
        filters = config.get("branch_filters")
        if not isinstance(filters, dict):
            filters = {}
        if include is not None:
            filters["include"] = list(include)
        if exclude is not None:
            filters["exclude"] = list(exclude)
        config["branch_filters"] = filters
        self.set_config(repo_id, config)

    def get_branch_filters(self, repo_id: int) -> tuple[list[str], list[str]]:
        """Return (include_patterns, exclude_patterns) for a repository."""
        config = self.get_config(repo_id)
        filters = config.get("branch_filters", {})
        if isinstance(filters, dict):
            include = filters.get("include") or config.get("include") or []
            exclude = filters.get("exclude") or config.get("exclude") or []
        else:
            include = config.get("include") or []
            exclude = config.get("exclude") or []
        return list(include), list(exclude)

    def resolve_priority_chain(self, repo_id: int) -> list[str]:
        """Resolve ordered merge priority chain for a repository."""
        config = self.get_config(repo_id)
        if not config:
            return ["main"]

        # Support priority_chain directly
        if "priority_chain" in config and isinstance(config["priority_chain"], list):
            return config["priority_chain"] if config["priority_chain"] else ["main"]

        hierarchy = config.get("hierarchy", {})
        if isinstance(hierarchy, list):
            return hierarchy if hierarchy else ["main"]

        if isinstance(hierarchy, dict):
            if "priority_chain" in hierarchy and isinstance(hierarchy["priority_chain"], list):
                return hierarchy["priority_chain"] if hierarchy["priority_chain"] else ["main"]
            chain: list[str] = []
            if "development" in hierarchy:
                chain.append(hierarchy["development"])
            if "staging" in hierarchy:
                chain.append(hierarchy["staging"])
            if "production" in hierarchy:
                chain.append(hierarchy["production"])
            if chain:
                return chain

        return ["main"]
