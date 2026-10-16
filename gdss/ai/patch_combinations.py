"""Deterministic patch-strategy enumeration by conflict topology."""

from __future__ import annotations

from gdss.ai.types import ConflictTopology, PatchCombination

_STRATEGIES: dict[str, tuple[tuple[str, str], ...]] = {
    "union": (
        ("take both", "take_both"),
        ("take i then j", "i_then_j"),
        ("take j then i", "j_then_i"),
    ),
    "intersection": (
        ("take common", "take_common"),
        ("keep i, drop j", "keep_i_drop_j"),
        ("keep j, drop i", "keep_j_drop_i"),
    ),
    "disjoint": (
        ("keep i", "keep_i"),
        ("keep j", "keep_j"),
        ("keep neither", "keep_neither"),
    ),
    "asymmetric": (
        ("take i then j", "i_then_j"),
        ("take j then i", "j_then_i"),
    ),
}


def enumerate_combinations(topology: ConflictTopology) -> list[PatchCombination]:
    """Return viable resolution strategies without producing patch text."""
    return [
        PatchCombination(label=label, strategy=strategy)
        for label, strategy in _STRATEGIES[topology.kind]
    ]
