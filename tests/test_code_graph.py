import pytest
from gdss.graph.code_graph import CodeGraph
from gdss.core.transform_types import CodeSymbol, SymbolType


def _helper_symbol() -> CodeSymbol:
    sym = CodeSymbol(name="helper", type=SymbolType.FUNCTION, start_line=1, end_line=3, calls=[])
    sym.ensure_identity("utils.py")
    return sym


def test_code_graph_dependencies():
    graph = CodeGraph()

    helper = _helper_symbol()
    graph.add_file_symbols("utils.py", [helper])
    helper_id = helper.symbol_id

    run = CodeSymbol(name="run", type=SymbolType.FUNCTION, start_line=3, end_line=6, calls=["helper", "internal_func"])
    internal = CodeSymbol(name="internal_func", type=SymbolType.FUNCTION, start_line=8, end_line=10, calls=[])
    run.ensure_identity("app.py")
    internal.ensure_identity("app.py")

    app_symbols = [
        CodeSymbol(name="utils", type=SymbolType.IMPORT, start_line=1, end_line=1, module="utils"),
        run,
        internal,
    ]
    graph.add_file_symbols("app.py", app_symbols)

    graph.resolve_calls()

    assert "utils.py" in graph.g
    assert "app.py" in graph.g
    assert helper_id in graph.g
    assert run.symbol_id in graph.g
    assert internal.symbol_id in graph.g

    assert graph.g.has_edge("utils.py", helper_id)
    assert graph.g.has_edge("app.py", run.symbol_id)
    assert graph.g.has_edge("app.py", "utils")
    assert graph.g.has_edge(run.symbol_id, helper_id)
    assert graph.g.has_edge(run.symbol_id, internal.symbol_id)

    helper_impact = graph.get_downstream_impact(helper_id)
    assert run.symbol_id in helper_impact

    run_impact = graph.get_downstream_impact(run.symbol_id)
    assert helper_id not in run_impact


def test_file_move_preserves_symbol_identity():
    graph = CodeGraph()
    helper = _helper_symbol()
    graph.add_file_symbols("src/utils/calc.py", [helper])
    original_id = helper.symbol_id

    moved_helper = CodeSymbol(
        name="helper",
        type=SymbolType.FUNCTION,
        start_line=1,
        end_line=3,
        signature=helper.signature,
        parent_class=helper.parent_class,
        calls=helper.calls,
        structural_tokens=helper.structural_tokens,
        language=helper.language,
    )
    moved_helper.ensure_identity("src/helpers/calc.py")

    graph.add_file_symbols("src/helpers/calc.py", [moved_helper])

    assert moved_helper.symbol_id == original_id
    assert original_id in graph.g
    assert graph.g.nodes[original_id]["chart_location"] == "src/helpers/calc.py"
    assert graph.get_display_id(original_id) == "src/helpers/calc.py::helper"
