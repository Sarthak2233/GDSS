"""Export CodeGraph to external formats."""

from __future__ import annotations

import json
from typing import Any

from gdss.graph.code_graph import CodeGraph


class UnsupportedGraphFormatError(ValueError):
    """Raised when an export format is not supported."""


def export_graph(graph: CodeGraph, format: str, output_path: str) -> str:
    """Write a CodeGraph to disk. Returns the output path."""
    fmt = format.lower().strip()
    if fmt == "dot":
        content = render_dot(graph)
    elif fmt == "json":
        content = render_json(graph)
    else:
        raise UnsupportedGraphFormatError(
            f"Unsupported export format '{format}'. Supported formats: dot, json."
        )

    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return output_path


def render_dot(graph: CodeGraph) -> str:
    """Render a Graphviz DOT document with human-readable node labels."""
    lines = ["digraph GDSS {"]
    lines.append('  graph [rankdir=LR, fontname="Segoe UI"];')
    lines.append('  node [shape=box, style=rounded, fontname="Segoe UI"];')
    lines.append('  edge [fontname="Segoe UI"];')

    for node_id, data in graph.g.nodes(data=True):
        label = _node_label(graph, node_id, data)
        lines.append(f'  "{_escape_dot(node_id)}" [label="{_escape_dot(label)}"];')

    for source, target, data in graph.g.edges(data=True):
        relation = data.get("relation", "")
        edge_attrs = f' [label="{_escape_dot(relation)}"]' if relation else ""
        lines.append(
            f'  "{_escape_dot(source)}" -> "{_escape_dot(target)}"{edge_attrs};'
        )

    lines.append("}")
    return "\n".join(lines) + "\n"


def render_json(graph: CodeGraph) -> str:
    """Render a JSON snapshot of the graph."""
    return json.dumps(graph.snapshot(), indent=2, sort_keys=True) + "\n"


def _node_label(graph: CodeGraph, node_id: str, data: dict[str, Any]) -> str:
    if data.get("type") == "file":
        return str(data.get("chart_location") or data.get("file") or node_id)
    return graph.get_display_id(node_id)


def _escape_dot(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
