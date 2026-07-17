"""Vectorized cosine similarity / distance over embedding matrices."""

from __future__ import annotations

import numpy as np


def _as_2d(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=np.float64)
    if a.ndim == 1:
        return a.reshape(1, -1)
    if a.ndim != 2:
        raise ValueError("expected 1-D or 2-D array")
    return a


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """
    Pairwise cosine similarity.
    - If both 1-D: returns scalar shape ().
    - If a is (n,d) and b is (m,d): returns (n, m).
    - If a is (n,d) and b is 1-D: returns (n,).
    """
    a2 = _as_2d(a)
    b2 = _as_2d(b)
    a_norm = a2 / np.maximum(np.linalg.norm(a2, axis=1, keepdims=True), 1e-12)
    b_norm = b2 / np.maximum(np.linalg.norm(b2, axis=1, keepdims=True), 1e-12)
    sim = a_norm @ b_norm.T
    if a.ndim == 1 and b.ndim == 1:
        return np.asarray(sim[0, 0])
    if b.ndim == 1:
        return sim[:, 0]
    if a.ndim == 1:
        return sim[0, :]
    return sim


def cosine_distance(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """1 - cosine_similarity (same shape rules)."""
    return 1.0 - cosine_similarity(a, b)
