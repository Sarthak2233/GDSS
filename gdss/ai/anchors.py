"""Resolve semantic operators to exact, committed target-frame anchors."""

from __future__ import annotations

import hashlib
from pathlib import PurePosixPath

from gdss.ai.types import SuggestionAnchor
from gdss.core.ast_parser import ASTParser
from gdss.core.transform_types import CodeSymbol, SemanticOperator
from gdss.watcher.git_observer import GitObserver


def _symbol_digest(symbol: CodeSymbol) -> str:
    payload = "\x1f".join(
        (
            symbol.symbol_id or "",
            symbol.signature,
            symbol.body,
            str(symbol.start_line),
            str(symbol.end_line),
            str(symbol.start_column),
            str(symbol.end_column),
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _find_symbol(
    symbols: list[CodeSymbol], operator: SemanticOperator
) -> CodeSymbol | None:
    by_id = {symbol.symbol_id: symbol for symbol in symbols if symbol.symbol_id}
    for symbol_id in (
        operator.to_symbol_id,
        operator.symbol_id,
        operator.from_symbol_id,
    ):
        if symbol_id and symbol_id in by_id:
            return by_id[symbol_id]

    names = {
        name
        for name in (
            operator.to_name,
            operator.name,
            operator.from_name,
            operator.get_target_name(),
        )
        if name
    }
    candidates = [symbol for symbol in symbols if symbol.name in names]
    return min(candidates, key=lambda symbol: (symbol.start_line, symbol.start_column)) if candidates else None


def resolve_anchor(
    observer: GitObserver,
    parser: ASTParser,
    operator: SemanticOperator,
    target_branch: str,
) -> SuggestionAnchor | None:
    """Resolve one operator against committed target-branch content without writing files."""
    path = PurePosixPath(operator.file)
    if path.is_absolute() or ".." in path.parts:
        return None
    content = observer.get_file_content_at_commit(target_branch, operator.file)
    if not isinstance(content, str):
        return None
    symbol = _find_symbol(parser.parse_file(operator.file, content), operator)
    if symbol is None:
        return None
    return SuggestionAnchor(
        file_path=str(path),
        line_start=symbol.start_line,
        line_end=symbol.end_line,
        column_start=symbol.start_column,
        column_end=symbol.end_column,
        target_branch=target_branch,
        content_digest=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        symbol_digest=_symbol_digest(symbol),
    )
