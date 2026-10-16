import numpy as np

from gdss.core.transform_types import CodeSymbol, SymbolType
from gdss.embeddings.branch_vector import (
    aggregate_branch_tip,
    embed_symbols,
    embedding_distance_to_attractor,
)
from gdss.embeddings.encoder import DeterministicBagEncoder


def _sym(name: str, body: str, sid: str | None = None) -> CodeSymbol:
    s = CodeSymbol(
        name=name,
        type=SymbolType.FUNCTION,
        start_line=1,
        end_line=2,
        signature="()",
        body=body,
        structural_tokens=["return_statement"],
    )
    s.ensure_identity("mod.py")
    if sid:
        s.symbol_id = sid
    return s


def test_embed_symbols_and_self_distance_zero():
    enc = DeterministicBagEncoder(dim=64)
    symbols = [
        _sym("alpha", "def alpha():\n    return 1"),
        _sym("beta", "def beta():\n    return 2"),
    ]
    emb = embed_symbols(symbols, enc)
    assert len(emb) == 2
    tip = aggregate_branch_tip(list(emb.values()), branch="feature")
    assert tip.symbol_count == 2
    assert tip.dim == 64
    dist = embedding_distance_to_attractor(tip.vector, tip.vector)
    assert np.isclose(dist, 0.0)


def test_different_tips_have_positive_distance():
    enc = DeterministicBagEncoder(dim=64)
    a = embed_symbols([_sym("a", "def a():\n    validate_card()\n    charge()")], enc)
    b = embed_symbols([_sym("b", "def b():\n    pass")], enc)
    tip_a = aggregate_branch_tip(list(a.values()), branch="a")
    tip_b = aggregate_branch_tip(list(b.values()), branch="b")
    dist = embedding_distance_to_attractor(tip_a.vector, tip_b.vector)
    assert dist > 0.0
