"""Build a CodeGraph by walking a repository."""

from __future__ import annotations

import os

from gdss.core.ast_parser import ASTParser
from gdss.graph.code_graph import CodeGraph

SOURCE_EXTENSIONS = (".py", ".js", ".ts", ".jsx", ".tsx")
SKIP_DIR_NAMES = {".git", "venv", "__pycache__", "node_modules", ".venv"}


def build_code_graph_from_repo(repo_path: str) -> CodeGraph:
    """Parse source files under repo_path and resolve call edges."""
    graph = CodeGraph()
    parser = ASTParser()
    root_path = os.path.abspath(repo_path)

    for root, dirs, files in os.walk(root_path):
        dirs[:] = [name for name in dirs if name not in SKIP_DIR_NAMES]
        for filename in files:
            if not filename.endswith(SOURCE_EXTENSIONS):
                continue
            absolute_path = os.path.join(root, filename)
            chart_location = os.path.relpath(absolute_path, root_path)
            try:
                symbols = parser.parse_file(absolute_path)
                graph.add_file_symbols(chart_location, symbols)
            except OSError:
                continue

    graph.resolve_calls()
    return graph
