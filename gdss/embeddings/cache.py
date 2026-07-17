"""Content-hash LRU cache wrapping a CodeEncoder (batch miss → one encode call)."""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from collections.abc import Sequence

import numpy as np

from gdss.embeddings.encoder import CodeEncoder


class EmbeddingCache:
    """LRU keyed by SHA-256 of text; encodes only cache misses in one batch."""

    def __init__(self, encoder: CodeEncoder, max_size: int = 256):
        self.encoder = encoder
        self.max_size = max_size
        self._store: OrderedDict[str, np.ndarray] = OrderedDict()

    @staticmethod
    def _key(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        n = len(texts)
        if n == 0:
            return np.zeros((0, self.encoder.dim), dtype=np.float32)

        keys = [self._key(t) for t in texts]
        out = np.zeros((n, self.encoder.dim), dtype=np.float32)
        miss_idx: list[int] = []
        miss_texts: list[str] = []

        for i, key in enumerate(keys):
            if key in self._store:
                self._store.move_to_end(key)  # dsa:ignore
                out[i] = self._store[key]
            else:
                miss_idx.append(i)
                miss_texts.append(texts[i])

        if miss_texts:
            encoded = self.encoder.encode_texts(miss_texts)
            for j, i in enumerate(miss_idx):
                vec = encoded[j]
                out[i] = vec
                key = keys[i]
                self._store[key] = vec.copy()
                self._store.move_to_end(key)  # dsa:ignore
                while len(self._store) > self.max_size:
                    self._store.popitem(last=False)

        return out
