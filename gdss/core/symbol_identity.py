"""Position-independent stable symbol identity for semantic graph nodes."""

from __future__ import annotations

import hashlib

from gdss.core.transform_types import CodeSymbol, SymbolType


def compute_symbol_id(
    symbol: CodeSymbol,
    language: str = "python",
) -> str:
    """
    Deterministic symbol GUID independent of file path (chart location).
    Based on language, type, parent scope, name, and normalized signature.
    """
    parent = symbol.parent_class or ""
    signature = _normalize_signature(symbol.signature)
    key = f"{language}:{symbol.type.value}:{parent}:{symbol.name}:{signature}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def _normalize_signature(signature: str | None) -> str:
    if not signature:
        return ""
    return " ".join(signature.split())


def is_graph_symbol_type(symbol_type: SymbolType) -> bool:
    return symbol_type in {SymbolType.FUNCTION, SymbolType.CLASS}
