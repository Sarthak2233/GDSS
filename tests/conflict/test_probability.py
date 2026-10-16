"""ConflictProbabilityEstimator: heuristic scoring without importing gdss.drift."""

from gdss.conflict.probability import ConflictProbability, ConflictProbabilityEstimator
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


def test_zero_score_with_no_overlap():
    est = ConflictProbabilityEstimator()
    result = est.estimate(
        branch_ops=[_op(OperatorType.ADD_FUNCTION, file="a.py", name="alpha")],
        reference_ops=[_op(OperatorType.ADD_FUNCTION, file="b.py", name="beta")],
        shared_files=[],
        drift_magnitude=0.0,
    )
    assert result.score == 0.0
    assert result.reasons == ()


def test_high_score_with_shared_files_rename_and_drift():
    est = ConflictProbabilityEstimator()
    result = est.estimate(
        branch_ops=[
            _op(OperatorType.MODIFY_FUNCTION, file="auth.py", name="verify_token"),
            _op(
                OperatorType.RENAME_FUNCTION,
                file="auth.py",
                name=None,
                from_name="old_fn",
                to_name="new_fn",
            ),
        ],
        reference_ops=[
            _op(OperatorType.MODIFY_FUNCTION, file="auth.py", name="verify_token"),
            _op(OperatorType.DELETE_FUNCTION, file="auth.py", name="old_fn"),
        ],
        shared_files=["auth.py"],
        drift_magnitude=0.8,
    )
    assert result.score > 0.5
    assert 0.0 <= result.score <= 1.0
    assert any("shared" in r.lower() or "file" in r.lower() for r in result.reasons)
    assert any("drift" in r.lower() for r in result.reasons)


def test_reasons_enumerate_contributing_factors():
    est = ConflictProbabilityEstimator()
    result = est.estimate(
        branch_ops=[_op(OperatorType.MODIFY_FUNCTION, file="x.py", name="f")],
        reference_ops=[_op(OperatorType.MODIFY_FUNCTION, file="x.py", name="f")],
        shared_files=["x.py"],
        drift_magnitude=0.4,
    )
    assert len(result.reasons) >= 1
    assert isinstance(result, ConflictProbability)
