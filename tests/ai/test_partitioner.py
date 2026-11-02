"""Unit tests for topological conflict partitioning."""

from __future__ import annotations

from gdss.ai.partitioner import partition_conflicts
from gdss.ai.types import Suggestion, SuggestionAnchor, SuggestionContext


def _make_sug(sug_id: str, file_path: str, symbol: str) -> Suggestion:
    return Suggestion(
        kind="conflict",
        file_path=file_path,
        line_start=1,
        line_end=10,
        symbol_id=f"{file_path}::{symbol}",
        operator="modify_function",
        action="review",
        rationale="conflict",
        reason=("collision",),
        confidence=0.9,
        anchor=SuggestionAnchor(file_path=file_path, line_start=1, line_end=10),
        context=SuggestionContext(
            reference_branch="main",
            candidate_branch="feature-a",
            omega=0.5,
            merge_risk=0.2,
            operator_i_id=f"op_{sug_id}_1",
            operator_j_id=f"op_{sug_id}_2",
        ),
        suggestion_id=sug_id,
    )


def test_partition_empty():
    assert partition_conflicts([]) == []


def test_partition_disjoint_files():
    s1 = _make_sug("sug_1", "services/auth.py", "login")
    s2 = _make_sug("sug_2", "services/billing.py", "charge")
    s3 = _make_sug("sug_3", "frontend/app.ts", "render")

    clusters = partition_conflicts([s1, s2, s3])
    assert len(clusters) == 3
    # Each disjoint file is an independent cluster
    for c in clusters:
        assert c.is_independent is True
        assert len(c.suggestions) == 1


def test_partition_same_file_coupled():
    s1 = _make_sug("sug_1", "services/auth.py", "login")
    s2 = _make_sug("sug_2", "services/auth.py", "verify_token")
    s3 = _make_sug("sug_3", "services/billing.py", "charge")

    clusters = partition_conflicts([s1, s2, s3])
    assert len(clusters) == 2

    auth_cluster = next(c for c in clusters if c.file_path == "services/auth.py")
    assert len(auth_cluster.suggestions) == 2
    assert [s.suggestion_id for s in auth_cluster.suggestions] == ["sug_1", "sug_2"]

    billing_cluster = next(c for c in clusters if c.file_path == "services/billing.py")
    assert len(billing_cluster.suggestions) == 1
    assert billing_cluster.suggestions[0].suggestion_id == "sug_3"
