from gdss.ai.geodesic import minimize_omega_sequence, plan_merge_order
from gdss.ai.semantic_rebase import build_transport_plan, parallel_transport
from gdss.core.transform_types import OperatorType, SemanticOperator


def test_parallel_transport_drops_already_applied_commuting_operator():
    op = SemanticOperator(OperatorType.MODIFY_FUNCTION, "a.py", name="run")
    assert parallel_transport([op], [op]) == []


def test_transport_plan_remaps_file_renames_and_ignores_timestamps():
    source_operator = SemanticOperator(OperatorType.MODIFY_FUNCTION, "old.py", name="run")
    equivalent_frame_operator = SemanticOperator(OperatorType.MODIFY_FUNCTION, "old.py", name="run")
    rename = SemanticOperator(
        OperatorType.RENAME_FILE,
        "renamed.py",
        from_name="old.py",
        to_name="renamed.py",
    )

    applied = build_transport_plan([source_operator], [equivalent_frame_operator])
    remapped = build_transport_plan([source_operator], [rename])

    assert applied.kept == ()
    assert applied.already_applied == (source_operator,)
    assert remapped.kept[0].file == "renamed.py"
    assert remapped.file_remaps == {"old.py": "renamed.py"}


def test_minimize_omega_sequence_orders_by_lowest_next_cost():
    ops = ["a", "b", "c"]
    costs = {("a", "b"): 0.9, ("a", "c"): 0.1, ("c", "b"): 0.2}
    assert minimize_omega_sequence(ops, costs) == ["a", "c", "b"]


def test_merge_order_plan_reports_a_stable_heuristic_and_cost_comparison():
    ops = ["a", "b", "c"]
    costs = {("a", "b"): 0.3, ("a", "c"): 0.1, ("b", "c"): 0.3}

    plan = plan_merge_order(ops, costs)

    assert plan.order == ("a", "c", "b")
    assert plan.proposed_cost < plan.baseline_cost
    assert plan.heuristic == "greedy_nearest_neighbor"
    assert [step.omega for step in plan.steps] == [0.1, 0.3]
