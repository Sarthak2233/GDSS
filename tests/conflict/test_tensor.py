"""TensorEngine sparse Omega_ij."""

from gdss.conflict.tensor import TensorEngine
from gdss.core.transform_types import OperatorType, SemanticOperator


def _op(
    operator: OperatorType,
    file: str = "a.py",
    name: str | None = "fn",
) -> SemanticOperator:
    return SemanticOperator(operator=operator, file=file, name=name)


def test_shared_modified_file_positive_omega():
    engine = TensorEngine()
    branch_ops = {
        "feature": [_op(OperatorType.MODIFY_FUNCTION, file="auth.py", name="login")],
        "main": [_op(OperatorType.MODIFY_FUNCTION, file="auth.py", name="logout")],
    }
    result = engine.compute(branch_ops, drift_magnitudes={})
    assert ("feature", "main") in result.entries or ("main", "feature") in result.entries
    entry = next(iter(result.entries.values()))
    assert entry.omega > 0
    assert result.merge_risk > 0


def test_disjoint_branches_no_off_diagonal_entry():
    engine = TensorEngine()
    branch_ops = {
        "a": [_op(OperatorType.ADD_FUNCTION, file="a.py", name="alpha")],
        "b": [_op(OperatorType.ADD_FUNCTION, file="b.py", name="beta")],
    }
    result = engine.compute(branch_ops, drift_magnitudes={})
    off = {k: v for k, v in result.entries.items() if k[0] != k[1]}
    assert off == {}


def test_merge_risk_equals_sum_of_entries():
    engine = TensorEngine()
    branch_ops = {
        "feature": [_op(OperatorType.MODIFY_FUNCTION, file="x.py", name="f")],
        "main": [_op(OperatorType.MODIFY_FUNCTION, file="x.py", name="g")],
    }
    result = engine.compute(branch_ops, drift_magnitudes={"feature": 0.4, "main": 0.2})
    assert abs(result.merge_risk - sum(e.omega for e in result.entries.values())) < 1e-9


def test_drift_on_diagonal():
    engine = TensorEngine()
    branch_ops = {
        "feature": [_op(OperatorType.ADD_FUNCTION, file="a.py", name="alpha")],
        "main": [_op(OperatorType.ADD_FUNCTION, file="b.py", name="beta")],
    }
    result = engine.compute(
        branch_ops, drift_magnitudes={"feature": 0.55, "main": 0.33}
    )
    assert ("feature", "feature") in result.entries
    assert result.entries[("feature", "feature")].omega == 0.55
    assert ("main", "main") in result.entries
    assert result.entries[("main", "main")].omega == 0.33


def test_sparse_only_nonzero():
    engine = TensorEngine()
    branch_ops = {
        "a": [_op(OperatorType.ADD_FUNCTION, file="a.py", name="alpha")],
        "b": [_op(OperatorType.ADD_FUNCTION, file="b.py", name="beta")],
    }
    result = engine.compute(branch_ops, drift_magnitudes={"a": 0.0, "b": 0.0})
    for entry in result.entries.values():
        assert entry.omega > 0
    # zero drift diagonals omitted
    assert ("a", "a") not in result.entries
