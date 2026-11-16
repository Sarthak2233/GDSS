"""Deterministic Semantic Impact Closure (SIC) Engine (Phase 1).

Transitively expands conflict symbols across dependency callers, contract interfaces,
and test suites with relevance edge weighting and token-budget pruning.
Runs strictly on local CPU with zero tokens and zero external API dependencies.
"""

from __future__ import annotations

import fnmatch
import re
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from gdss.core.config import ImpactClosureConfig
from gdss.logger import get_logger

if TYPE_CHECKING:
    from gdss.graph.code_graph import CodeGraph

logger = get_logger("gdss.graph.impact_closure")

# Relevance edge weights
WEIGHT_DIRECT_CALL = 1.00
WEIGHT_TYPE_ANNOTATION = 0.95
WEIGHT_TEST_COVERAGE = 0.90
WEIGHT_IMPORT = 0.50
WEIGHT_LEXICAL = 0.25

# Token estimation heuristics
TOKENS_PER_SYMBOL = 250
TOKENS_PER_TEST = 150
TOKENS_PER_CONTRACT = 150

# Multi-language test suite and directory indicators
_TEST_FILE_INDICATORS = frozenset(
    {
        "tests/",
        "test/",
        "__tests__/",
        "src/test/",
        "testdata/",
        "spec/",
        "specs/",
        "unit/",
        "integration/",
        ".tests/",
        "/tests",
        "/test",
    }
)

_TEST_FILE_NAME_PATTERNS = re.compile(
    r"(?:^|[/\\])(?:test[_\-\.]|[a-z0-9_]+[_\-\.]test|[a-z0-9_]+[_\-\.]spec|[a-z0-9_]+tests?)\.[a-z0-9]+$",
    re.IGNORECASE,
)

# Multi-language API contracts, schemas, RPC, and route definitions
_CONTRACT_EXTENSIONS = frozenset(
    {
        ".proto",
        ".graphql",
        ".gql",
        ".thrift",
        ".avsc",
        ".sql",
        ".prisma",
        ".openapi.json",
        ".openapi.yaml",
        ".openapi.yml",
        ".swagger.json",
    }
)

_CONTRACT_FILE_INDICATORS = frozenset(
    {
        "routes",
        "route",
        "endpoints",
        "endpoint",
        "controllers",
        "controller",
        "schema",
        "schemas",
        "api/",
        "/api/",
        "models",
        "model",
        "entities",
        "entity",
        "dto",
        "dtos",
        "interfaces",
        "interface",
        "contracts",
        "contract",
        "serializers",
        "serializer",
        "repositories",
        "repository",
        "protobuf",
        "grpc",
    }
)


@dataclass(frozen=True)
class ClosureNode:
    """A node inside the semantic impact closure."""

    symbol_id: str
    file_path: str
    node_type: str  # "function", "class", "contract", "test", "file"
    hop_distance: int
    weight: float
    implicated_by: str
    relation: str = "calls"


@dataclass(frozen=True)
class ImpactClosureResult:
    """The complete confidence-bounded Semantic Impact Closure envelope."""

    conflict_symbols: tuple[str, ...]
    closure_nodes: tuple[ClosureNode, ...]
    implicated_files: tuple[str, ...]
    target_tests: tuple[str, ...]
    contract_files: tuple[str, ...]
    total_estimated_tokens: int

    def get_nodes_by_hop(self, hop: int) -> list[ClosureNode]:
        """Filter closure nodes by specific hop distance."""
        return [n for n in self.closure_nodes if n.hop_distance == hop]


def is_test_path(path: str, custom_patterns: Sequence[str] = ()) -> bool:
    """Determine if a file or symbol path belongs to a test suite in any supported language.

    Evaluates explicit .gdss.yml test_patterns first (Tier 1); falls back to built-in
    multi-language heuristics as the final resort (Tier 2).
    """
    norm = path.replace("\\", "/").lower()

    # Tier 1: Explicit user-configured glob patterns from .gdss.yml
    for pattern in custom_patterns:
        norm_pat = pattern.replace("\\", "/").lower()
        if fnmatch.fnmatch(norm, norm_pat) or fnmatch.fnmatch(path, pattern):
            return True

    # Tier 2 (Final Resort): Built-in multi-language directory and filename heuristics
    if any(indicator in norm for indicator in _TEST_FILE_INDICATORS):
        return True
    if _TEST_FILE_NAME_PATTERNS.search(norm):
        return True
    base = norm.split("/")[-1]
    if base.endswith(
        (
            "test.py",
            "test.ts",
            "test.tsx",
            "test.js",
            "test.jsx",
            "test.go",
            "test.rs",
            "test.java",
            "test.cs",
            "tests.cs",
            "test.cpp",
            "test.c",
        )
    ):
        return True
    return False


def is_contract_path(path: str, custom_patterns: Sequence[str] = ()) -> bool:
    """Determine if a file path represents an API route, schema, or contract in any supported language.

    Evaluates explicit .gdss.yml contract_patterns first (Tier 1); falls back to built-in
    multi-language heuristics as the final resort (Tier 2).
    """
    norm = path.replace("\\", "/").lower()

    # Tier 1: Explicit user-configured glob patterns from .gdss.yml
    for pattern in custom_patterns:
        norm_pat = pattern.replace("\\", "/").lower()
        if fnmatch.fnmatch(norm, norm_pat) or fnmatch.fnmatch(path, pattern):
            return True

    # Tier 2 (Final Resort): Built-in multi-language contract heuristics
    if any(norm.endswith(ext) for ext in _CONTRACT_EXTENSIONS):
        return True
    if any(indicator in norm for indicator in _CONTRACT_FILE_INDICATORS):
        return True
    base = path.split("/")[-1].split("\\")[-1]
    # C# Interface naming convention (e.g. IPaymentService.cs)
    if base.startswith("I") and len(base) > 2 and base[1].isupper() and base.endswith((".cs", ".ts")):
        return True
    return False


def compute_semantic_impact_closure(
    code_graph: CodeGraph,
    conflict_symbols: list[str],
    max_hops: int = 2,
    relevance_threshold: float = 0.70,
    token_budget: int = 4000,
    config: ImpactClosureConfig | None = None,
) -> ImpactClosureResult:
    """Compute the transitive 2-hop Semantic Impact Closure over a CodeGraph.

    Args:
        code_graph: The repository's analyzed CodeGraph.
        conflict_symbols: Directly collided AST symbol IDs or names (C_0).
        max_hops: Maximum transitive caller depth (default: 2 hops).
        relevance_threshold: Edge weight cutoff for transitive propagation (default: 0.70).
        token_budget: Maximum token budget for context assembly.
        config: Optional repository ImpactClosureConfig loaded from .gdss.yml.

    Returns:
        ImpactClosureResult containing the closure nodes, files, and test mappings.
    """
    if config is not None:
        max_hops = config.max_hops
        relevance_threshold = config.relevance_threshold
        token_budget = config.token_budget

    custom_tests = config.test_patterns if config else ()
    custom_contracts = config.contract_patterns if config else ()

    g = code_graph.g
    g_rev = g.reverse(copy=False)

    visited_nodes: dict[str, ClosureNode] = {}
    queue: deque[tuple[str, int, float, str]] = deque()

    # Step 1: Initialize Hop 0 (Conflict Symbols C_0)
    for sym in conflict_symbols:
        resolved_id = sym
        if sym not in g:
            find_res = code_graph.find_node_by_name(sym)
            if find_res:
                resolved_id = find_res

        node_data = g.nodes.get(resolved_id, {})
        file_path = node_data.get("chart_location") or node_data.get("file") or ""
        raw_type = node_data.get("type", "function")

        if is_test_path(file_path, custom_patterns=custom_tests):
            node_type = "test"
        elif is_contract_path(file_path, custom_patterns=custom_contracts):
            node_type = "contract"
        else:
            node_type = raw_type

        node = ClosureNode(
            symbol_id=resolved_id,
            file_path=file_path,
            node_type=node_type,
            hop_distance=0,
            weight=1.0,
            implicated_by=resolved_id,
            relation="conflict",
        )
        visited_nodes[resolved_id] = node
        if resolved_id in g:
            queue.append((resolved_id, 0, 1.0, resolved_id))

    # Step 2: Traverse reverse call/dependency graph up to max_hops
    while queue:
        curr_id, current_hop, current_weight, source_id = queue.popleft()
        if current_hop >= max_hops:
            continue

        next_hop = current_hop + 1

        for neighbor in g_rev.neighbors(curr_id):
            edge_data = g_rev.get_edge_data(curr_id, neighbor) or {}
            relation = str(edge_data.get("relation", "calls"))

            # Calculate edge weight based on relationship semantics
            neighbor_data = g.nodes.get(neighbor, {})
            neighbor_file = neighbor_data.get("chart_location") or neighbor_data.get("file") or ""

            if is_test_path(neighbor_file, custom_patterns=custom_tests) or is_test_path(neighbor, custom_patterns=custom_tests):
                edge_weight = WEIGHT_TEST_COVERAGE
                node_type = "test"
            elif is_contract_path(neighbor_file, custom_patterns=custom_contracts):
                edge_weight = WEIGHT_TYPE_ANNOTATION
                node_type = "contract"
            elif relation == "calls":
                edge_weight = WEIGHT_DIRECT_CALL
                node_type = neighbor_data.get("type", "function")
            elif relation in {"implements", "annotates", "type"}:
                edge_weight = WEIGHT_TYPE_ANNOTATION
                node_type = neighbor_data.get("type", "class")
            elif relation == "imports":
                edge_weight = WEIGHT_IMPORT
                node_type = "file"
            else:
                edge_weight = WEIGHT_LEXICAL
                node_type = neighbor_data.get("type", "unknown")

            # Ignore structural file -> node containment edges in reverse
            if relation == "defines":
                continue

            propagated_weight = current_weight * edge_weight
            if propagated_weight < relevance_threshold and next_hop > 1:
                continue

            # Upsert into visited nodes if new or higher weight
            if (
                neighbor not in visited_nodes
                or propagated_weight > visited_nodes[neighbor].weight
                or next_hop < visited_nodes[neighbor].hop_distance
            ):
                candidate_node = ClosureNode(
                    symbol_id=neighbor,
                    file_path=neighbor_file,
                    node_type=node_type,
                    hop_distance=next_hop,
                    weight=propagated_weight,
                    implicated_by=curr_id,
                    relation=relation,
                )
                visited_nodes[neighbor] = candidate_node

                if next_hop < max_hops:
                    queue.append((neighbor, next_hop, propagated_weight, curr_id))

    # Step 3: Token Estimation & Budget-Aware Pruning
    def estimate_node_tokens(n: ClosureNode) -> int:
        if n.node_type == "test":
            return TOKENS_PER_TEST
        if n.node_type == "contract":
            return TOKENS_PER_CONTRACT
        return TOKENS_PER_SYMBOL

    all_nodes = list(visited_nodes.values())
    tokens_by_node = {n.symbol_id: estimate_node_tokens(n) for n in all_nodes}
    total_tokens = sum(tokens_by_node.values())

    if total_tokens > token_budget:
        logger.info(
            "Semantic Impact Closure estimated tokens (%d) exceed budget (%d). Pruning.",
            total_tokens,
            token_budget,
        )

        def node_priority(n: ClosureNode) -> tuple[int, float]:
            # Priority tuple: (hop_priority, weight)
            # Hop 0 = 3 (highest, never prune)
            # Tests = 2
            # Hop 1 = 1
            # Hop 2 = 0 (prune first)
            if n.hop_distance == 0:
                p = 3
            elif n.node_type == "test":
                p = 2
            elif n.hop_distance == 1:
                p = 1
            else:
                p = 0
            return (p, n.weight)

        # Sort ascending by priority so lowest priority nodes are at the front
        all_nodes.sort(key=node_priority)
        pruned_nodes: list[ClosureNode] = []
        accumulated_tokens = 0

        # Select from highest priority downwards
        for n in reversed(all_nodes):
            cost = tokens_by_node.get(n.symbol_id, estimate_node_tokens(n))  # dsa:ignore
            if n.hop_distance == 0 or (accumulated_tokens + cost <= token_budget):
                pruned_nodes.append(n)
                accumulated_tokens += cost
            else:
                logger.debug(
                    "Pruning closure node %s (hop=%d, weight=%.2f) to stay within budget",
                    n.symbol_id,
                    n.hop_distance,
                    n.weight,
                )

        all_nodes = pruned_nodes
        total_tokens = accumulated_tokens

    # Step 4: Extract deduplicated files and test suites
    implicated_files = sorted(
        {n.file_path for n in all_nodes if n.file_path and n.file_path != "."}
    )
    target_tests = sorted(
        {n.file_path for n in all_nodes if n.node_type == "test" and n.file_path}
    )
    contract_files = sorted(
        {n.file_path for n in all_nodes if n.node_type == "contract" and n.file_path}
    )

    return ImpactClosureResult(
        conflict_symbols=tuple(conflict_symbols),
        closure_nodes=tuple(all_nodes),
        implicated_files=tuple(implicated_files),
        target_tests=tuple(target_tests),
        contract_files=tuple(contract_files),
        total_estimated_tokens=total_tokens,
    )
