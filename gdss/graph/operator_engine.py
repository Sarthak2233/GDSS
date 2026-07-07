"""Apply and invert semantic operators on CodeGraph."""

from __future__ import annotations

import copy
from typing import Any, Dict, Optional

from gdss.core.transform_types import CodeSymbol, OperatorType, SemanticOperator, SymbolType
from gdss.graph.code_graph import CodeGraph


class UnsupportedOperatorError(Exception):
    """Raised when apply/invert is not implemented for an operator type."""


def apply_operator(op: SemanticOperator, graph: CodeGraph) -> None:
    handler = _APPLY_HANDLERS.get(op.operator)
    if handler is None:
        raise UnsupportedOperatorError(f"apply() not supported for {op.operator}")
    handler(op, graph)


def invert_operator(op: SemanticOperator) -> SemanticOperator:
    handler = _INVERT_HANDLERS.get(op.operator)
    if handler is None:
        raise UnsupportedOperatorError(f"invert() not supported for {op.operator}")
    return handler(op)


def _apply_rename_function(op: SemanticOperator, graph: CodeGraph) -> None:
    node_id = op.from_symbol_id or graph.find_node_by_name(op.from_name, op.file)
    if not node_id or node_id not in graph.g:
        return
    data = graph.g.nodes[node_id]
    old_name = data.get("name")
    graph.g.nodes[node_id]["name"] = op.to_name
    if old_name and old_name in graph._symbol_index:
        graph._symbol_index[old_name].discard(node_id)
        if not graph._symbol_index[old_name]:
            del graph._symbol_index[old_name]
    graph._symbol_index.setdefault(op.to_name, set()).add(node_id)


def _apply_delete_function(op: SemanticOperator, graph: CodeGraph) -> None:
    node_id = op.symbol_id or graph.find_node_by_name(op.name, op.file)
    if node_id and node_id in graph.g:
        graph._remove_node(node_id)


def _apply_add_function(op: SemanticOperator, graph: CodeGraph) -> None:
    sym = CodeSymbol(
        name=op.name or "",
        type=SymbolType.FUNCTION,
        start_line=0,
        end_line=0,
        signature=op.details.get("signature", ""),
        parent_class=op.details.get("parent_class"),
        chart_location=op.file,
        symbol_id=op.symbol_id,
    )
    sym.ensure_identity(op.file)
    graph.add_file_symbols(op.file, [sym])


def _apply_modify_function(op: SemanticOperator, graph: CodeGraph) -> None:
    node_id = op.symbol_id or graph.find_node_by_name(op.name, op.file)
    if not node_id or node_id not in graph.g:
        return
    if op.details.get("signature_changed"):
        graph.g.nodes[node_id]["signature"] = op.details.get(
            "new_signature", graph.g.nodes[node_id].get("signature")
        )
    if op.details.get("changed_blocks"):
        graph.g.nodes[node_id]["changed_blocks"] = list(op.details["changed_blocks"])


def _apply_rename_class(op: SemanticOperator, graph: CodeGraph) -> None:
    _apply_rename_function(op, graph)


def _apply_delete_class(op: SemanticOperator, graph: CodeGraph) -> None:
    _apply_delete_function(op, graph)


def _apply_add_class(op: SemanticOperator, graph: CodeGraph) -> None:
    sym = CodeSymbol(
        name=op.name or "",
        type=SymbolType.CLASS,
        start_line=0,
        end_line=0,
        signature=op.details.get("signature", ""),
        chart_location=op.file,
        symbol_id=op.symbol_id,
    )
    sym.ensure_identity(op.file)
    graph.add_file_symbols(op.file, [sym])


def _apply_modify_class(op: SemanticOperator, graph: CodeGraph) -> None:
    _apply_modify_function(op, graph)


def _invert_rename(op: SemanticOperator) -> SemanticOperator:
    return SemanticOperator(
        operator=op.operator,
        file=op.file,
        commit=op.commit,
        from_name=op.to_name,
        to_name=op.from_name,
        from_symbol_id=op.to_symbol_id,
        to_symbol_id=op.from_symbol_id,
        details=copy.deepcopy(op.details),
        author=op.author,
    )


def _invert_add(op: SemanticOperator, delete_type: OperatorType) -> SemanticOperator:
    return SemanticOperator(
        operator=delete_type,
        file=op.file,
        commit=op.commit,
        name=op.name,
        symbol_id=op.symbol_id,
        details=copy.deepcopy(op.details),
        author=op.author,
    )


def _invert_delete(op: SemanticOperator, add_type: OperatorType) -> SemanticOperator:
    return SemanticOperator(
        operator=add_type,
        file=op.file,
        commit=op.commit,
        name=op.name,
        symbol_id=op.symbol_id,
        details=copy.deepcopy(op.details),
        author=op.author,
    )


def _invert_modify(op: SemanticOperator) -> SemanticOperator:
    inverted_details = copy.deepcopy(op.details)
    if "old_signature" in inverted_details and "new_signature" in inverted_details:
        inverted_details["old_signature"], inverted_details["new_signature"] = (
            inverted_details["new_signature"],
            inverted_details["old_signature"],
        )
    if "changed_blocks" in inverted_details:
        inverted_details["changed_blocks"] = inverted_details.get("previous_blocks", [])
    return SemanticOperator(
        operator=op.operator,
        file=op.file,
        commit=op.commit,
        name=op.name,
        symbol_id=op.symbol_id,
        details=inverted_details,
        author=op.author,
    )


_APPLY_HANDLERS = {
    OperatorType.RENAME_FUNCTION: _apply_rename_function,
    OperatorType.DELETE_FUNCTION: _apply_delete_function,
    OperatorType.ADD_FUNCTION: _apply_add_function,
    OperatorType.MODIFY_FUNCTION: _apply_modify_function,
    OperatorType.RENAME_CLASS: _apply_rename_class,
    OperatorType.DELETE_CLASS: _apply_delete_class,
    OperatorType.ADD_CLASS: _apply_add_class,
    OperatorType.MODIFY_CLASS: _apply_modify_class,
}

_INVERT_HANDLERS = {
    OperatorType.RENAME_FUNCTION: _invert_rename,
    OperatorType.RENAME_CLASS: _invert_rename,
    OperatorType.ADD_FUNCTION: lambda op: _invert_add(op, OperatorType.DELETE_FUNCTION),
    OperatorType.DELETE_FUNCTION: lambda op: _invert_delete(op, OperatorType.ADD_FUNCTION),
    OperatorType.ADD_CLASS: lambda op: _invert_add(op, OperatorType.DELETE_CLASS),
    OperatorType.DELETE_CLASS: lambda op: _invert_delete(op, OperatorType.ADD_CLASS),
    OperatorType.MODIFY_FUNCTION: _invert_modify,
    OperatorType.MODIFY_CLASS: _invert_modify,
}
