import pytest
from gdss.graph.code_graph import CodeGraph
from gdss.core.transform_types import CodeSymbol, SymbolType

def test_code_graph_dependencies():
    graph = CodeGraph()

    # Define mock symbols for 'utils.py'
    utils_symbols = [
        CodeSymbol(name="helper", type=SymbolType.FUNCTION, start_line=1, end_line=3, calls=[])
    ]
    graph.add_file_symbols("utils.py", utils_symbols)

    # Define mock symbols for 'app.py' (imports utils, has global function that calls helper)
    app_symbols = [
        CodeSymbol(name="utils", type=SymbolType.IMPORT, start_line=1, end_line=1, module="utils"),
        CodeSymbol(name="run", type=SymbolType.FUNCTION, start_line=3, end_line=6, calls=["helper", "internal_func"]),
        CodeSymbol(name="internal_func", type=SymbolType.FUNCTION, start_line=8, end_line=10, calls=[])
    ]
    graph.add_file_symbols("app.py", app_symbols)

    graph.resolve_calls()
    summary = graph.get_summary()

    # Verify nodes
    assert "utils.py" in graph.g
    assert "app.py" in graph.g
    assert "utils.py::helper" in graph.g
    assert "app.py::run" in graph.g
    assert "app.py::internal_func" in graph.g

    # Check edges
    #defines
    assert graph.g.has_edge("utils.py", "utils.py::helper")
    assert graph.g.has_edge("app.py", "app.py::run")

    #imports
    assert graph.g.has_edge("app.py", "utils")

    #calls
    # run calls helper
    assert graph.g.has_edge("app.py::run", "utils.py::helper")
    # run calls internal_func
    assert graph.g.has_edge("app.py::run", "app.py::internal_func")

    # Test Downstream Impact:
    # Modifying helper should propagate downstream impact to run
    helper_impact = graph.get_downstream_impact("utils.py::helper")
    assert "app.py::run" in helper_impact

    # Modifying run should not affect helper
    run_impact = graph.get_downstream_impact("app.py::run")
    assert "utils.py::helper" not in run_impact
