"""Build a CodeGraph by walking a repository."""

from __future__ import annotations

import os
from typing import Dict

from gdss.core.ast_parser import ASTParser, SOURCE_EXTENSIONS
from gdss.graph.code_graph import CodeGraph

SKIP_DIR_NAMES = {".git", "venv", "__pycache__", "node_modules", ".venv"}


def build_code_graph_from_repo(
    repo_path: str,
    *,
    progress_callback=None,
    batch_size: int = 500,
) -> CodeGraph:
    """Parse source files under repo_path and resolve call edges.

    progress_callback(done, total, skipped_summary) is optional for large repos.
    """
    graph = CodeGraph()
    parser = ASTParser()
    root_path = os.path.abspath(repo_path)

    file_list = []
    skipped_unsupported: Dict[str, int] = {}
    for root, dirs, files in os.walk(root_path):
        dirs[:] = [name for name in dirs if name not in SKIP_DIR_NAMES]
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            absolute_path = os.path.join(root, filename)
            if ext not in SOURCE_EXTENSIONS:
                # Count likely source-ish extensions that we cannot parse
                if ext and ext not in {".md", ".txt", ".json", ".yml", ".yaml", ".toml", ".lock"}:
                    skipped_unsupported[ext] = skipped_unsupported.get(ext, 0) + 1
                continue
            file_list.append(absolute_path)

    total = len(file_list)
    for idx, absolute_path in enumerate(file_list, start=1):
        chart_location = os.path.relpath(absolute_path, root_path)
        try:
            symbols = parser.parse_file(absolute_path)
            graph.add_file_symbols(chart_location, symbols)
        except OSError:
            continue
        if progress_callback and (idx % batch_size == 0 or idx == total):
            progress_callback(idx, total, dict(skipped_unsupported))

    graph.resolve_calls()
    # Attach skipped summary for CLI callers
    graph.skipped_unsupported = skipped_unsupported  # type: ignore[attr-defined]
    graph.parser_skipped = parser.consume_skipped_summary()  # type: ignore[attr-defined]
    return graph
