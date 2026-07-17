"""CodeEncoder protocol and deterministic bag-of-tokens encoder."""

from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

import numpy as np

DEFAULT_DIM = 384
_TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@runtime_checkable
class CodeEncoder(Protocol):
    """Batched text → φ(C) ∈ R^{n×d}. Implementations must not loop inference per item without batching."""

    @property
    def dim(self) -> int: ...

    @property
    def name(self) -> str: ...

    def encode_texts(self, texts: Sequence[str]) -> np.ndarray:
        """Return shape (n, d), rows L2-normalized."""
        ...


class DeterministicBagEncoder:
    """
    Offline CI-friendly encoder: hash bag of tokens into fixed R^d, L2-normalized.
    Stable for identical text; no network or ONNX required.
    """

    def __init__(self, dim: int = DEFAULT_DIM):
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def name(self) -> str:
        return "bag"

    def encode_texts(self, texts: Sequence[str]) -> np.ndarray:
        n = len(texts)
        if n == 0:
            return np.zeros((0, self._dim), dtype=np.float32)
        out = np.zeros((n, self._dim), dtype=np.float32)
        for i, text in enumerate(texts):
            out[i] = self._encode_one(text)
        # Vectorized L2 normalize
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-12)
        return out / norms

    def _encode_one(self, text: str) -> np.ndarray:
        vec = np.zeros(self._dim, dtype=np.float32)
        tokens = _TOKEN_RE.findall(text.lower())
        if not tokens:
            # Still produce a non-zero vector from raw bytes
            digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).digest()
            for j in range(0, min(len(digest), self._dim)):
                vec[j % self._dim] += digest[j] / 255.0
            return vec
        for tok in tokens:
            h = hashlib.sha256(tok.encode("utf-8")).digest()
            # Map 32 bytes into several bins for denser bag
            for k in range(0, 32, 4):
                idx = int.from_bytes(h[k : k + 4], "little") % self._dim
                sign = 1.0 if (h[k] & 1) == 0 else -1.0
                vec[idx] += sign
        return vec


def get_encoder(backend: str | None = None, dim: int = DEFAULT_DIM) -> CodeEncoder:
    """
    Factory: default DeterministicBagEncoder.
    Use GDSS_EMBEDDING_BACKEND=onnx (or backend='onnx') for OnnxMiniLMEncoder when available.
    """
    choice = (backend or os.environ.get("GDSS_EMBEDDING_BACKEND", "bag")).strip().lower()
    if choice == "onnx":
        try:
            from gdss.embeddings.onnx_encoder import OnnxMiniLMEncoder

            return OnnxMiniLMEncoder(dim=dim)
        except Exception as exc:
            raise RuntimeError(
                "WHAT: ONNX embedding backend requested but unavailable.\n"
                "WHY: onnxruntime missing, model file missing, or load failed.\n"
                f"FIX: pip install -e '.[embeddings]' and place MiniLM ONNX under .gdss/models/, "
                f"or unset GDSS_EMBEDDING_BACKEND to use bag. Detail: {exc}"
            ) from exc
    return DeterministicBagEncoder(dim=dim)
