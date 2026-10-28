"""Tests verifying that non-code asset operators correctly feed the Conflict Tensor."""

from __future__ import annotations

from gdss.conflict.commutativity import CommutativityClass, classify
from gdss.conflict.tensor import TensorEngine
from gdss.core.transform_types import OperatorType, SemanticOperator


def test_independent_package_json_additions_commute():
    op_a = SemanticOperator(
        operator=OperatorType.ADD_DEPENDENCY,
        file="package.json",
        name="axios",
        details={"version": "^1.6.0"},
    )
    op_b = SemanticOperator(
        operator=OperatorType.ADD_DEPENDENCY,
        file="package.json",
        name="lodash",
        details={"version": "^4.17.21"},
    )

    # Independent packages do not contact -> INDEPENDENT
    assert classify(op_a, op_b) == CommutativityClass.INDEPENDENT


def test_clashing_package_json_additions_interfere():
    op_a = SemanticOperator(
        operator=OperatorType.ADD_DEPENDENCY,
        file="package.json",
        name="axios",
        details={"version": "^1.6.0"},
    )
    op_b = SemanticOperator(
        operator=OperatorType.ADD_DEPENDENCY,
        file="package.json",
        name="axios",
        details={"version": "^2.0.0"},
    )

    # Same package name contacts -> INTERFERE
    assert classify(op_a, op_b) == CommutativityClass.INTERFERE


def test_migration_split_head_hazard_interferes():
    # Both branches branch off 0022_initial
    op_a = SemanticOperator(
        operator=OperatorType.MIGRATION_STEP,
        file="alembic/versions/0023_roles.py",
        name="migration_parent::0022_initial",
        details={"parent_revision": "0022_initial", "revision": "0023_roles"},
    )
    op_b = SemanticOperator(
        operator=OperatorType.MIGRATION_STEP,
        file="alembic/versions/0024_audit.py",
        name="migration_parent::0022_initial",
        details={"parent_revision": "0022_initial", "revision": "0024_audit"},
    )

    # Same migration parent contacts -> INTERFERE
    assert classify(op_a, op_b) == CommutativityClass.INTERFERE

    # Check tensor computation
    engine = TensorEngine()
    branch_ops = {
        "PR#1": [op_a],
        "PR#2": [op_b],
    }
    drift_map = {"PR#1": 0.5, "PR#2": 0.5}
    tensor = engine.compute(branch_ops, drift_map)
    entry = tensor.entries.get(("PR#1", "PR#2"))
    assert entry is not None
    assert entry.omega > 0.0
