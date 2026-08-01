"""operator_interference over op-sets."""

from gdss.conflict.commutativity import operator_interference
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


def test_rename_delete_collision_counts_one_interfere():
    branch = [
        _op(
            OperatorType.RENAME_FUNCTION,
            name=None,
            from_name="foo",
            to_name="bar",
        )
    ]
    other = [_op(OperatorType.DELETE_FUNCTION, name="foo")]
    interfering, contacts = operator_interference(branch, other)
    assert interfering == 1
    assert contacts == 1


def test_disjoint_sets_zero_interference():
    branch = [_op(OperatorType.ADD_FUNCTION, file="a.py", name="alpha")]
    other = [_op(OperatorType.ADD_FUNCTION, file="b.py", name="beta")]
    interfering, contacts = operator_interference(branch, other)
    assert interfering == 0
    assert contacts == 0
