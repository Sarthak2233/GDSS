import json

import pytest

from gdss.core.transform_types import CodeSymbol, SymbolType
from gdss.graph.code_graph import CodeGraph
from gdss.graph.graph_export import UnsupportedGraphFormatError, export_graph


def _build_sample_graph() -> CodeGraph:
    graph = CodeGraph()
    helper = CodeSymbol(name="helper", type=SymbolType.FUNCTION, start_line=1, end_line=3, calls=[])
    helper.ensure_identity("utils.py")
    run = CodeSymbol(
        name="run",
        type=SymbolType.FUNCTION,
        start_line=3,
        end_line=6,
        calls=["helper"],
    )
    run.ensure_identity("app.py")
    graph.add_file_symbols("utils.py", [helper])
    graph.add_file_symbols("app.py", [run])
    graph.resolve_calls()
    return graph


def test_export_dot_writes_human_readable_labels(tmp_path):
    graph = _build_sample_graph()
    output = tmp_path / "graph.dot"

    written = export_graph(graph, format="dot", output_path=str(output))

    text = output.read_text(encoding="utf-8")
    assert written == str(output)
    assert "digraph GDSS" in text
    assert "utils.py::helper" in text
    assert "app.py::run" in text
    assert 'label="calls"' in text


def test_export_json_writes_snapshot(tmp_path):
    graph = _build_sample_graph()
    output = tmp_path / "graph.json"

    export_graph(graph, format="json", output_path=str(output))

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "nodes" in payload
    assert "edges" in payload
    assert any(node.get("name") == "helper" for node in payload["nodes"].values())


def test_export_unsupported_format_raises():
    graph = _build_sample_graph()

    with pytest.raises(UnsupportedGraphFormatError):
        export_graph(graph, format="graphml", output_path="out.graphml")
