from __future__ import annotations

from pathlib import Path

import pytest

from gdss.ai.suggestion_store import (
    is_suggestion_stale,
    list_suggestions,
    load_suggestion,
    save_suggestion,
)
from gdss.ai.types import (
    ConflictTopology,
    PatchCombination,
    Suggestion,
    SuggestionAnchor,
    SuggestionContext,
)


@pytest.fixture
def sample_suggestion() -> Suggestion:
    anchor = SuggestionAnchor(
        file_path="services/auth.py",
        line_start=15,
        line_end=25,
        target_branch="feature/auth",
        content_digest="abc123digest",
    )
    context = SuggestionContext(
        reference_branch="main",
        candidate_branch="feature/auth",
        omega=0.75,
        merge_risk=0.5,
        operator_i_id="op_i",
        operator_j_id="op_j",
    )
    topology = ConflictTopology(
        kind="intersection",
        symbol_id="services/auth.py::login",
        operator_i="modify_function",
        operator_j="change_signature",
        commutativity="interfere",
        justification="both branches touch login signature",
    )
    combo = PatchCombination(
        label="reconcile",
        strategy="adapt_signature",
        patch_text="--- a/services/auth.py\n+++ b/services/auth.py\n@@ -15,5 +15,5 @@\n-def login(user):\n+def login(user, timeout=30):\n",
        source="llm",
        validated=True,
        validation_status="validated",
    )
    return Suggestion(
        kind="conflict",
        file_path="services/auth.py",
        line_start=15,
        line_end=25,
        symbol_id="services/auth.py::login",
        operator="modify_function",
        action="reconcile signatures",
        rationale="overlapping modifications",
        reason=("collision detected",),
        confidence=0.88,
        anchor=anchor,
        context=context,
        topology=topology,
        patch_combinations=[combo],
        validated=True,
    )


def test_save_and_load_suggestion(tmp_path: Path, sample_suggestion: Suggestion):
    target_commit = "9f8e7d6c5b4a3210fedcba9876543210abcdef01"
    saved_path = save_suggestion(sample_suggestion, tmp_path, target_commit=target_commit)

    assert saved_path.is_file()
    assert saved_path.parent == tmp_path / ".gdss" / "suggestions"
    assert saved_path.suffix == ".json"

    loaded = load_suggestion(sample_suggestion.suggestion_id, tmp_path)
    assert loaded is not None
    assert loaded["id"] == sample_suggestion.suggestion_id
    assert loaded["file_path"] == "services/auth.py"
    assert loaded["target_commit"] == target_commit
    assert loaded["validated"] is True
    assert len(loaded["strategies"]) == 1
    assert loaded["strategies"][0]["label"] == "reconcile"
    # Local source includes patch text for apply
    assert "patch_text" in loaded["patch_combinations"][0]


def test_list_suggestions(tmp_path: Path, sample_suggestion: Suggestion):
    # Initially empty
    assert list_suggestions(tmp_path) == []

    # Save one
    save_suggestion(sample_suggestion, tmp_path, target_commit="commit1")

    summaries = list_suggestions(tmp_path)
    assert len(summaries) == 1
    assert summaries[0]["id"] == sample_suggestion.suggestion_id
    assert summaries[0]["file_path"] == "services/auth.py"
    assert summaries[0]["target_commit"] == "commit1"


def test_is_suggestion_stale(sample_suggestion: Suggestion):
    current_head = "9f8e7d6c5b4a3210fedcba9876543210abcdef01"
    stale_head = "1111111111111111111111111111111111111111"

    data = {
        "id": sample_suggestion.suggestion_id,
        "target_commit": current_head,
    }

    assert is_suggestion_stale(data, current_head) is False
    assert is_suggestion_stale(data, stale_head) is True
    # Missing target commit is considered stale
    assert is_suggestion_stale({"id": "foo"}, current_head) is True
