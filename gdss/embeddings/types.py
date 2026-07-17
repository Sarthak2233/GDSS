"""Embedding value types."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EmbeddingVector:
    """A single φ(C) vector with provenance."""

    vector: np.ndarray
    dim: int
    source_id: str
    backend: str = "bag"

    def __post_init__(self) -> None:
        if self.vector.ndim != 1:
            raise ValueError("EmbeddingVector.vector must be 1-D")
        if self.vector.shape[0] != self.dim:
            raise ValueError(f"dim mismatch: vector {self.vector.shape[0]} != dim {self.dim}")


@dataclass(frozen=True)
class BranchTipVector:
    """Aggregated tip embedding for a branch (mean of symbol bodies, L2-normalized)."""

    vector: np.ndarray
    dim: int
    branch: str
    symbol_count: int
    reference_branch: str | None = None
