from gdss.ai.patch_combinations import enumerate_combinations
from gdss.ai.types import ConflictTopology


def test_enumerate_combinations_returns_deterministic_disjoint_strategies():
    topology = ConflictTopology(
        kind="disjoint",
        symbol_id="src/payments.py::process",
        operator_i="rename_function",
        operator_j="delete_function",
        commutativity="interfere",
        justification="rename conflicts with deletion",
    )

    combinations = enumerate_combinations(topology)

    assert [combination.strategy for combination in combinations] == [
        "keep_i",
        "keep_j",
        "keep_neither",
    ]
    assert all(combination.patch_text is None for combination in combinations)
