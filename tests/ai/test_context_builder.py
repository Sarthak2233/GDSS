"""Tests for 3-way semantic collision context extraction."""

from __future__ import annotations

from unittest.mock import MagicMock

from gdss.ai.context_builder import (
    SemanticCollisionContext,
    extract_3way_symbol_context,
)
from gdss.ai.types import (
    ConflictTopology,
    Suggestion,
    SuggestionAnchor,
    SuggestionContext,
)
from gdss.core.ast_parser import ASTParser
from gdss.core.transform_types import OperatorType, SemanticOperator
from gdss.drift.context import AnalysisContext


def _make_mock_analysis_context(
    base_file_content: str | None,
    branch_a_content: str | None,
    branch_b_content: str | None,
    file_path: str = "app/service.py",
    reference_branch: str = "main",
    branch_a: str = "feature/alpha",
    branch_b: str = "feature/beta",
) -> AnalysisContext:
    observer = MagicMock()

    def get_content(commit_or_ref: str, path: str) -> str | None:
        if path != file_path:
            return None
        if commit_or_ref == reference_branch:
            return base_file_content
        if commit_or_ref == branch_a:
            return branch_a_content
        if commit_or_ref == branch_b:
            return branch_b_content
        return None

    observer.get_file_content_at_commit.side_effect = get_content
    observer.repo_path = "/mock/repo"

    parser = ASTParser()
    extractor = MagicMock()
    tensor = MagicMock()

    op_a = SemanticOperator(
        operator=OperatorType.MODIFY_FUNCTION,
        file=file_path,
        name="calculate",
    )
    op_b = SemanticOperator(
        operator=OperatorType.MODIFY_FUNCTION,
        file=file_path,
        name="calculate",
    )
    caller_op = SemanticOperator(
        operator=OperatorType.ADD_DEPENDENCY,
        file="app/caller.py",
        name="run_calc",
        details={"to": "calculate"},
    )

    return AnalysisContext(
        repo_path="/mock/repo",
        reference_branch=reference_branch,
        active_branch=branch_a,
        branches=(reference_branch, branch_a, branch_b),
        branch_operators={
            branch_a: (op_a,),
            branch_b: (op_b, caller_op),
        },
        drift_magnitudes={branch_a: 0.4, branch_b: 0.6},
        tensor=tensor,
        observer=observer,
        parser=parser,
        extractor=extractor,
        branch_commits={
            branch_a: (
                {"sha": "aaa111", "summary": "Update calculate in alpha", "author": "Alice"},
            ),
            branch_b: ({"sha": "bbb222", "summary": "Update calculate in beta", "author": "Bob"},),
        },
        branch_intents={
            branch_a: {
                "title": "PR #10: Alpha calc",
                "description": "Add factor parameter",
                "author": "Alice",
            },
            branch_b: {
                "title": "PR #11: Beta calc",
                "description": "Add offset parameter",
                "author": "Bob",
            },
        },
    )


def test_extract_3way_symbol_context_all_branches_present():
    base_code = "def calculate(x: int) -> int:\n    return x\n"
    branch_a_code = "def calculate(x: int, factor: int = 1) -> int:\n    return x * factor\n"
    branch_b_code = "def calculate(x: int, offset: int = 0) -> int:\n    return x + offset\n"

    file_path = "app/service.py"
    ctx = _make_mock_analysis_context(
        base_file_content=base_code,
        branch_a_content=branch_a_code,
        branch_b_content=branch_b_code,
        file_path=file_path,
    )

    topology = ConflictTopology(
        "union",
        "app/service.py::calculate",
        "modify_function",
        "modify_function",
        "interfere",
        "divergent signatures and bodies",
    )
    suggestion = Suggestion(
        kind="conflict",
        file_path=file_path,
        line_start=1,
        line_end=2,
        symbol_id="app/service.py::calculate",
        operator="modify_function",
        action="reconcile",
        rationale="signature divergence",
        reason=("both branches modify calculate",),
        confidence=0.9,
        topology=topology,
        anchor=SuggestionAnchor(
            file_path=file_path,
            line_start=1,
            line_end=2,
            target_branch="feature/alpha",
        ),
        context=SuggestionContext(
            reference_branch="main",
            candidate_branch="feature/alpha",
            omega=0.85,
            merge_risk=1.2,
            operator_i_id="op_a",
            operator_j_id="op_b",
            other_branch="feature/beta",
        ),
    )

    extracted: SemanticCollisionContext = extract_3way_symbol_context(ctx, suggestion)

    assert extracted.file_path == file_path
    assert extracted.symbol_name == "calculate"
    assert extracted.language == "python"
    assert extracted.base_branch == "main"
    assert extracted.branch_a_name == "feature/alpha"
    assert extracted.branch_b_name == "feature/beta"

    # Verify 3-way symbol definitions
    assert "return x" in extracted.base_code
    assert "factor: int = 1" in extracted.branch_a_code
    assert "offset: int = 0" in extracted.branch_b_code

    # Verify line ranges
    assert extracted.base_line_range == (1, 2)
    assert extracted.branch_a_line_range == (1, 2)
    assert extracted.branch_b_line_range == (1, 2)

    # Verify impacted callers
    assert any(
        "caller.py" in caller or "run_calc" in caller for caller in extracted.impacted_callers
    )


def test_extract_3way_symbol_context_added_in_branches_missing_in_base():
    base_code = "# Empty file in main\n"
    branch_a_code = "def new_feature():\n    return 'alpha'\n"
    branch_b_code = "def new_feature():\n    return 'beta'\n"

    file_path = "app/feature.py"
    ctx = _make_mock_analysis_context(
        base_file_content=base_code,
        branch_a_content=branch_a_code,
        branch_b_content=branch_b_code,
        file_path=file_path,
    )

    suggestion = Suggestion(
        kind="conflict",
        file_path=file_path,
        line_start=1,
        line_end=2,
        symbol_id="app/feature.py::new_feature",
        operator="add_function",
        action="reconcile",
        rationale="concurrent additions",
        reason=("both branches add new_feature",),
        confidence=0.88,
        anchor=SuggestionAnchor(
            file_path=file_path,
            line_start=1,
            line_end=2,
            target_branch="feature/alpha",
        ),
        context=SuggestionContext(
            reference_branch="main",
            candidate_branch="feature/alpha",
            omega=0.75,
            merge_risk=0.9,
            operator_i_id="op_a",
            operator_j_id="op_b",
            other_branch="feature/beta",
        ),
    )

    extracted = extract_3way_symbol_context(ctx, suggestion)

    assert extracted.symbol_name == "new_feature"
    assert extracted.base_code == ""
    assert extracted.base_line_range is None
    assert "alpha" in extracted.branch_a_code
    assert "beta" in extracted.branch_b_code


def test_extract_3way_symbol_context_with_budget_condensation():
    # Long function that should be condensed when max_chars is small
    long_body = "\n".join(f"    line_{i} = {i}" for i in range(200))
    branch_a_code = f"def huge_function():\n{long_body}\n    return 42\n"

    file_path = "app/huge.py"
    ctx = _make_mock_analysis_context(
        base_file_content="",
        branch_a_content=branch_a_code,
        branch_b_content="",
        file_path=file_path,
    )

    suggestion = Suggestion(
        kind="conflict",
        file_path=file_path,
        line_start=1,
        line_end=202,
        symbol_id="app/huge.py::huge_function",
        operator="modify_function",
        action="reconcile",
        rationale="large diff",
        reason=("modify huge function",),
        confidence=0.8,
        anchor=SuggestionAnchor(
            file_path=file_path,
            line_start=1,
            line_end=202,
            target_branch="feature/alpha",
        ),
        context=SuggestionContext(
            reference_branch="main",
            candidate_branch="feature/alpha",
            omega=0.8,
            merge_risk=1.0,
            operator_i_id="op_a",
            operator_j_id="op_b",
            other_branch="feature/beta",
        ),
    )

    extracted = extract_3way_symbol_context(ctx, suggestion, max_code_chars=400)
    assert len(extracted.branch_a_code) < len(branch_a_code)
    assert "huge_function" in extracted.branch_a_code


def test_extract_3way_symbol_context_deleted_in_branch_b():
    base_code = "def old_calc():\n    return 10\n"
    branch_a_code = "def old_calc():\n    return 20\n"
    branch_b_code = "# Deleted old_calc in beta\n"

    file_path = "app/calc.py"
    ctx = _make_mock_analysis_context(
        base_file_content=base_code,
        branch_a_content=branch_a_code,
        branch_b_content=branch_b_code,
        file_path=file_path,
    )

    suggestion = Suggestion(
        kind="conflict",
        file_path=file_path,
        line_start=1,
        line_end=2,
        symbol_id="app/calc.py::old_calc",
        operator="modify_function",
        action="reconcile",
        rationale="modify vs delete",
        reason=("branch a modifies, branch b deletes",),
        confidence=0.85,
        anchor=SuggestionAnchor(
            file_path=file_path,
            line_start=1,
            line_end=2,
            target_branch="feature/alpha",
        ),
        context=SuggestionContext(
            reference_branch="main",
            candidate_branch="feature/alpha",
            omega=0.8,
            merge_risk=1.1,
            operator_i_id="op_a",
            operator_j_id="op_b",
            other_branch="feature/beta",
        ),
    )

    extracted = extract_3way_symbol_context(ctx, suggestion)
    assert "return 10" in extracted.base_code
    assert "return 20" in extracted.branch_a_code
    assert extracted.branch_b_code == ""
    assert extracted.branch_b_line_range is None


def test_extract_3way_symbol_context_typescript():
    base_code = "export function render(id: string): void {\n  console.log(id);\n}\n"
    branch_a_code = "export function render(id: string, theme: string = 'dark'): void {\n  console.log(id, theme);\n}\n"
    branch_b_code = "export function render(id: string, verbose?: boolean): void {\n  console.log(id, verbose);\n}\n"

    file_path = "src/render.ts"
    ctx = _make_mock_analysis_context(
        base_file_content=base_code,
        branch_a_content=branch_a_code,
        branch_b_content=branch_b_code,
        file_path=file_path,
    )

    suggestion = Suggestion(
        kind="conflict",
        file_path=file_path,
        line_start=1,
        line_end=3,
        symbol_id="src/render.ts::render",
        operator="modify_function",
        action="reconcile",
        rationale="signature divergence",
        reason=("both modify render",),
        confidence=0.9,
        anchor=SuggestionAnchor(
            file_path=file_path,
            line_start=1,
            line_end=3,
            target_branch="feature/alpha",
        ),
        context=SuggestionContext(
            reference_branch="main",
            candidate_branch="feature/alpha",
            omega=0.9,
            merge_risk=1.3,
            operator_i_id="op_a",
            operator_j_id="op_b",
            other_branch="feature/beta",
        ),
    )

    extracted = extract_3way_symbol_context(ctx, suggestion)
    assert extracted.language == "typescript"
    assert "theme" in extracted.branch_a_code
    assert "verbose" in extracted.branch_b_code
