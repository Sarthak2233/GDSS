from gdss.ai.conflict_topology import classify_conflict
from gdss.core.transform_types import OperatorType, SemanticOperator


def _operator(operator: OperatorType, name: str) -> SemanticOperator:
    return SemanticOperator(operator=operator, file="src/payments.py", name=name)


def test_classify_conflict_returns_union_for_commuting_disjoint_children():
    topology = classify_conflict(
        _operator(OperatorType.MODIFY_FUNCTION, "authorize"),
        _operator(OperatorType.MODIFY_FUNCTION, "capture"),
        symbol_overlap="same_parent_disjoint_children",
        symbol_id="src/payments.py::PaymentService",
    )

    assert topology.kind == "union"
    assert topology.commutativity == "commute"


def test_classify_conflict_returns_disjoint_for_rename_delete_same_symbol():
    topology = classify_conflict(
        SemanticOperator(
            operator=OperatorType.RENAME_FUNCTION,
            file="src/payments.py",
            from_name="process",
            to_name="process_payment",
        ),
        _operator(OperatorType.DELETE_FUNCTION, "process"),
        symbol_overlap="none",
        symbol_id="src/payments.py::process",
    )

    assert topology.kind == "disjoint"
    assert topology.commutativity == "interfere"


def test_classify_conflict_rejects_disjoint_child_hint_for_same_symbol_interference():
    topology = classify_conflict(
        SemanticOperator(
            operator=OperatorType.ADD_FUNCTION,
            file="src/payments.py",
            name="charge",
            details={"parent_class": "PaymentService"},
        ),
        SemanticOperator(
            operator=OperatorType.ADD_FUNCTION,
            file="src/payments.py",
            name="charge",
            details={"parent_class": "PaymentService"},
        ),
        symbol_overlap="same_parent_disjoint_children",
        symbol_id="src/payments.py::PaymentService::charge",
    )

    assert topology.kind == "disjoint"
    assert topology.commutativity == "interfere"


def test_classify_conflict_derives_intersection_from_overlapping_body_blocks():
    topology = classify_conflict(
        SemanticOperator(
            operator=OperatorType.MODIFY_FUNCTION,
            file="src/payments.py",
            name="process",
            symbol_id="src/payments.py::process",
            details={"changed_blocks": ["if_statement_0"]},
        ),
        SemanticOperator(
            operator=OperatorType.MODIFY_FUNCTION,
            file="src/payments.py",
            name="process",
            symbol_id="src/payments.py::process",
            details={"changed_blocks": ["if_statement_0"]},
        ),
        symbol_overlap=None,
        symbol_id="src/payments.py::process",
    )

    assert topology.kind == "intersection"
