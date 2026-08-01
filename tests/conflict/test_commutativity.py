"""Commutativity table and pairwise operator classification."""

from gdss.conflict.commutativity import (
    CommutativityClass,
    classify,
    commutativity_table,
)
from gdss.core.transform_types import OperatorType, SemanticOperator


def _op(
    operator: OperatorType,
    file: str = "a.py",
    name: str | None = "fn",
    from_name: str | None = None,
    to_name: str | None = None,
) -> SemanticOperator:
    return SemanticOperator(
        operator=operator,
        file=file,
        name=name,
        from_name=from_name,
        to_name=to_name,
    )


def test_rename_delete_same_symbol_interferes():
    a = _op(
        OperatorType.RENAME_FUNCTION,
        name=None,
        from_name="foo",
        to_name="bar",
    )
    b = _op(OperatorType.DELETE_FUNCTION, name="foo")
    assert classify(a, b) == CommutativityClass.INTERFERE


def test_modify_modify_same_symbol_commutes():
    a = _op(OperatorType.MODIFY_FUNCTION, name="foo")
    b = _op(OperatorType.MODIFY_FUNCTION, name="foo")
    assert classify(a, b) == CommutativityClass.COMMUTE


def test_add_add_different_symbols_independent():
    a = _op(OperatorType.ADD_FUNCTION, file="a.py", name="alpha")
    b = _op(OperatorType.ADD_FUNCTION, file="b.py", name="beta")
    assert classify(a, b) == CommutativityClass.INDEPENDENT


def test_commutativity_table_symmetric_for_same_type_pairs():
    table = commutativity_table()
    assert table
    for (ta, tb), cls in table.items():
        assert table[(tb, ta)] == cls
    # Spot-check documented rules
    assert (
        table[(OperatorType.RENAME_FUNCTION, OperatorType.DELETE_FUNCTION)]
        == CommutativityClass.INTERFERE
    )
    assert (
        table[(OperatorType.MODIFY_FUNCTION, OperatorType.MODIFY_FUNCTION)]
        == CommutativityClass.COMMUTE
    )
