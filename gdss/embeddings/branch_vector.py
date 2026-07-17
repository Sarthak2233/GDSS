"""Branch tip vectors and symbol embedding helpers (assistive Layer 6)."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import numpy as np

from gdss.core.transform_types import CodeSymbol
from gdss.embeddings.encoder import CodeEncoder
from gdss.embeddings.similarity import cosine_distance
from gdss.embeddings.types import BranchTipVector, EmbeddingVector


def _symbol_text(sym: CodeSymbol) -> str:
    parts = [sym.name or "", sym.signature or "", sym.body or ""]
    if sym.structural_tokens:
        parts.append(" ".join(sym.structural_tokens))
    return "\n".join(p for p in parts if p)


def embed_symbols(
    symbols: Sequence[CodeSymbol],
    encoder: CodeEncoder,
) -> dict[str, EmbeddingVector]:
    """Embed symbol bodies in one batch. Keys are symbol_id (ensured if missing)."""
    if not symbols:
        return {}
    texts: list[str] = []
    ids: list[str] = []
    for sym in symbols:
        sym.ensure_identity(sym.chart_location)
        sid = sym.symbol_id or f"{sym.parent_class or ''}::{sym.name}"
        ids.append(sid)
        texts.append(_symbol_text(sym))
    matrix = encoder.encode_texts(texts)
    result: dict[str, EmbeddingVector] = {}
    for i, sid in enumerate(ids):
        result[sid] = EmbeddingVector(
            vector=matrix[i].astype(np.float32),
            dim=encoder.dim,
            source_id=sid,
            backend=encoder.name,
        )
    return result


def aggregate_branch_tip(
    embeddings: Iterable[EmbeddingVector],
    branch: str,
    reference_branch: str | None = None,
) -> BranchTipVector:
    """Mean of symbol vectors, then L2-normalize. Empty → zero vector."""
    vecs = [e.vector for e in embeddings]
    if not vecs:
        dim = 0
        zero = np.zeros(0, dtype=np.float32)
        return BranchTipVector(
            vector=zero,
            dim=dim,
            branch=branch,
            symbol_count=0,
            reference_branch=reference_branch,
        )
    stacked = np.stack(vecs, axis=0).astype(np.float64)
    mean = stacked.mean(axis=0)
    norm = np.linalg.norm(mean)
    if norm < 1e-12:
        unit = mean.astype(np.float32)
    else:
        unit = (mean / norm).astype(np.float32)
    return BranchTipVector(
        vector=unit,
        dim=unit.shape[0],
        branch=branch,
        symbol_count=len(vecs),
        reference_branch=reference_branch,
    )


def embedding_distance_to_attractor(
    branch_tip: np.ndarray,
    attractor_tip: np.ndarray,
) -> float:
    """Assistive cosine distance between tip vectors (not continuous I(B_i))."""
    return float(cosine_distance(branch_tip, attractor_tip))
