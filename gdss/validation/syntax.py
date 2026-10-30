"""Multi-language AST syntax validator for candidate patches in GDSS."""

from __future__ import annotations

import ast
import os
from pathlib import Path

from tree_sitter import Node

from gdss.core.ast_parser import LANGUAGE_REGISTRY, ASTParser
from gdss.logger import get_logger
from gdss.validation.types import SyntaxCheckResult

logger = get_logger("gdss.validation.syntax")


def _find_first_error_node(node: Node) -> Node | None:
    """Recursively search for the first ERROR or missing node in a tree-sitter AST."""
    if not node.has_error:
        return None
    if node.type == "ERROR" or node.is_missing:
        return node
    for child in node.children:
        found = _find_first_error_node(child)
        if found is not None:
            return found
    return None


def validate_source_syntax(code: str, filename_or_path: str) -> SyntaxCheckResult:
    """Validate syntax of in-memory code string based on its filename/extension."""
    unknown_result = SyntaxCheckResult(valid=True, language="unknown")
    ext = os.path.splitext(filename_or_path)[1].lower().strip()
    if not ext:
        return unknown_result

    # Tier 1 / Native Python AST check
    if ext == ".py":
        try:
            ast.parse(code, filename=filename_or_path)
            return SyntaxCheckResult(valid=True, language="python")
        except SyntaxError as exc:
            msg = f"{exc.msg} at line {exc.lineno}" if exc.lineno else str(exc)
            return SyntaxCheckResult(
                valid=False,
                language="python",
                error_message=msg,
                line_number=exc.lineno,
            )
        except Exception as exc:
            return SyntaxCheckResult(
                valid=False,
                language="python",
                error_message=str(exc),  # dsa:ignore
            )

    # Tier 2 / Tree-sitter supported languages (.js, .jsx, .ts, .tsx, .go)
    if ext in LANGUAGE_REGISTRY:
        lang_name, _ = LANGUAGE_REGISTRY[ext]
        lang_clean_result = SyntaxCheckResult(valid=True, language=lang_name)
        parser = ASTParser.get_parser_for_ext(ext)
        if parser is None:
            return lang_clean_result

        try:
            tree = parser.parse(code.encode("utf-8", errors="replace"))
            root = tree.root_node
            if root.has_error:
                err_node = _find_first_error_node(root)
                line_no = (
                    (err_node.start_point[0] + 1)
                    if err_node is not None
                    else (root.start_point[0] + 1)
                )
                msg = f"Syntax error in {lang_name} at line {line_no}"
                return SyntaxCheckResult(
                    valid=False,
                    language=lang_name,
                    error_message=msg,
                    line_number=line_no,
                )
            return lang_clean_result
        except Exception as exc:
            return SyntaxCheckResult(
                valid=False,
                language=lang_name,
                error_message=str(exc),  # dsa:ignore
            )

    # Tier 3 / Unknown language without AST grammar
    return unknown_result


def validate_file_syntax(path: str | Path) -> SyntaxCheckResult:
    """Validate syntax of a file on disk."""
    p = Path(path)
    if not p.is_file():
        return SyntaxCheckResult(
            valid=False,
            language="unknown",
            error_message=f"File not found: {p}",
        )

    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return SyntaxCheckResult(
            valid=False,
            language="unknown",
            error_message=f"Could not read file {p}: {exc}",
        )

    return validate_source_syntax(content, p.name)
