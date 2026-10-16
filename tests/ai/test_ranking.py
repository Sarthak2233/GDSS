from gdss.ai.ranking import rank_tensor_entries
from gdss.conflict.tensor import ConflictTensor, TensorEntry


def test_rank_tensor_entries_orders_highest_omega_first_with_bounded_confidence():
    tensor = ConflictTensor(
        branches=("feature-a", "feature-b"),
        entries={
            ("feature-a", "feature-b"): TensorEntry(
                i="feature-a", j="feature-b", omega=0.8, reasons=("same_symbol",)
            ),
            ("feature-a", "feature-a"): TensorEntry(
                i="feature-a", j="feature-a", omega=0.2, reasons=("drift_self_energy",)
            ),
        },
        merge_risk=1.0,
    )

    ranked = rank_tensor_entries(tensor)

    assert [candidate.entry.omega for candidate in ranked] == [0.8, 0.2]
    assert all(0.0 <= candidate.confidence <= 1.0 for candidate in ranked)


def test_rank_tensor_entries_exposes_explainable_score_factors():
    tensor = ConflictTensor(
        branches=("feature-a", "feature-b"),
        entries={
            ("feature-a", "feature-b"): TensorEntry(
                i="feature-a",
                j="feature-b",
                omega=0.8,
                reasons=("same_symbol", "interference=1.00"),
            ),
        },
        merge_risk=0.8,
    )

    candidate = rank_tensor_entries(
        tensor,
        drift_magnitudes={"feature-a": 0.5, "feature-b": 1.0},
        anchor_confidence={("feature-a", "feature-b"): 0.75},
    )[0]

    assert candidate.factors["omega"] == 1.0
    assert candidate.factors["drift"] == 0.75
    assert candidate.factors["interference"] == 1.0
    assert candidate.factors["anchor"] == 0.75
