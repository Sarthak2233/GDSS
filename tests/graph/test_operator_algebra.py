
import pytest

from gdss.core.transform_types import CodeSymbol, OperatorType, SemanticOperator, SymbolType
from gdss.graph.code_graph import CodeGraph
from gdss.graph.operator_engine import UnsupportedOperatorError, apply_operator, invert_operator


def _make_graph_with_helper() -> tuple[CodeGraph, CodeSymbol]:
    graph = CodeGraph()
    helper = CodeSymbol(name="helper", type=SymbolType.FUNCTION, start_line=1, end_line=3, signature="()", calls=[])
    helper.ensure_identity("utils.py")
    graph.add_file_symbols("utils.py", [helper])
    return graph, helper


def test_operator_commutativity_identity():
    graph, helper = _make_graph_with_helper()
    initial = graph.snapshot()

    rename = SemanticOperator(
        operator=OperatorType.RENAME_FUNCTION,
        file="utils.py",
        from_name="helper",
        to_name="assist",
        from_symbol_id=helper.symbol_id,
        to_symbol_id=helper.symbol_id,
    )
    modify = SemanticOperator(
        operator=OperatorType.MODIFY_FUNCTION,
        file="utils.py",
        name="assist",
        symbol_id=helper.symbol_id,
        details={
            "signature_changed": True,
            "body_changed": False,
            "old_signature": "()",
            "new_signature": "(x)",
            "changed_blocks": [],
        },
    )

    apply_operator(rename, graph)
    apply_operator(modify, graph)

    inv_modify = invert_operator(modify)
    inv_rename = invert_operator(rename)
    apply_operator(inv_modify, graph)
    apply_operator(inv_rename, graph)

    final = graph.snapshot()
    assert final["nodes"][helper.symbol_id]["name"] == initial["nodes"][helper.symbol_id]["name"]


def test_rename_invert_swaps_names():
    op = SemanticOperator(
        operator=OperatorType.RENAME_FUNCTION,
        file="a.py",
        from_name="foo",
        to_name="bar",
        from_symbol_id="id1",
        to_symbol_id="id2",
    )
    inv = invert_operator(op)
    assert inv.from_name == "bar"
    assert inv.to_name == "foo"
    assert inv.from_symbol_id == "id2"
    assert inv.to_symbol_id == "id1"


def test_add_delete_are_inverses():
    add = SemanticOperator(
        operator=OperatorType.ADD_FUNCTION,
        file="a.py",
        name="foo",
        symbol_id="abc",
        details={"parent_class": None, "signature": "()"},
    )
    inv = invert_operator(add)
    assert inv.operator == OperatorType.DELETE_FUNCTION
    assert inv.name == "foo"


def test_unsupported_operator_raises():
    op = SemanticOperator(operator=OperatorType.ADD_IMPORT, file="a.py", name="os")
    graph = CodeGraph()
    with pytest.raises(UnsupportedOperatorError):
        apply_operator(op, graph)
