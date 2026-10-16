from gdss.ai.types import (
    ConflictTopology,
    PatchCombination,
    Suggestion,
    SuggestionAnchor,
    SuggestionContext,
)


def test_suggestion_defaults_to_unvalidated_deterministic_output():
    topology = ConflictTopology(
        kind="disjoint",
        symbol_id="src/payments.py::process",
        operator_i="rename_function",
        operator_j="delete_function",
        commutativity="interfere",
        justification="rename and deletion target the same symbol",
    )
    combination = PatchCombination(
        label="keep i",
        strategy="keep_i",
    )

    suggestion = Suggestion(
        kind="conflict",
        file_path="src/payments.py",
        line_start=10,
        line_end=20,
        symbol_id="src/payments.py::process",
        operator="rename_function",
        action="review the rename",
        rationale="The operators do not commute.",
        reason=("rename conflicts with deletion",),
        confidence=0.8,
        topology=topology,
        patch_combinations=[combination],
    )

    assert suggestion.validated is False
    assert suggestion.source == "deterministic"
    assert combination.validated is False
    assert combination.patch_text is None
    assert suggestion.topology is topology


def test_suggestion_has_a_stable_anchor_context_and_metadata_serializer():
    anchor = SuggestionAnchor(
        file_path="src/payments.py",
        line_start=10,
        line_end=20,
        column_start=5,
        column_end=1,
        target_branch="feature/payments",
        content_digest="content-digest",
        symbol_digest="symbol-digest",
    )
    context = SuggestionContext(
        reference_branch="main",
        candidate_branch="feature/payments",
        omega=0.8,
        merge_risk=1.2,
        operator_i_id="feature-op",
        operator_j_id="main-op",
    )
    combination = PatchCombination(
        label="keep i",
        strategy="keep_i",
        patch_text="--- a/src/payments.py\n+++ b/src/payments.py\n",
        source="llm",
        validated=True,
    )

    first = Suggestion(
        kind="conflict",
        file_path=anchor.file_path,
        line_start=anchor.line_start,
        line_end=anchor.line_end,
        symbol_id="src/payments.py::process",
        operator="modify_function",
        action="review",
        rationale="operators interfere",
        reason=("operators interfere",),
        confidence=0.8,
        anchor=anchor,
        context=context,
        patch_combinations=[combination],
    )
    second = Suggestion(
        kind="conflict",
        file_path=anchor.file_path,
        line_start=anchor.line_start,
        line_end=anchor.line_end,
        symbol_id="src/payments.py::process",
        operator="modify_function",
        action="review",
        rationale="operators interfere",
        reason=("operators interfere",),
        confidence=0.8,
        anchor=anchor,
        context=context,
    )

    metadata = first.to_metadata()

    assert first.suggestion_id == second.suggestion_id
    assert metadata["anchor"]["column_start"] == 5
    assert metadata["context"]["candidate_branch"] == "feature/payments"
    assert metadata["strategies"][0]["validated"] is True
    assert "patch_text" not in str(metadata)
