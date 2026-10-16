"""FAISS (or numpy fallback) vector store for symbol embeddings."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np

try:
    import faiss

    _HAS_FAISS = True
except ImportError:
    faiss = None
    _HAS_FAISS = False


def _l2_normalize(vectors: np.ndarray) -> np.ndarray:
    vectors = np.asarray(vectors, dtype=np.float32)
    if vectors.ndim == 1:
        vectors = vectors.reshape(1, -1)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return vectors / norms


class VectorStore:
    """
    Local ANN over L2-normalized vectors.
    Primary: FAISS IndexFlatIP (inner product ≡ cosine).
    Fallback: in-memory numpy brute-force when faiss-cpu is not installed.
    Persists under ``.gdss/vectors/`` as index.faiss (or vectors.npy) + id_map.json.
    """

    def __init__(self, dim: int, use_faiss: bool | None = None):
        self.dim = dim
        self._use_faiss = _HAS_FAISS if use_faiss is None else (use_faiss and _HAS_FAISS)
        self._id_to_int: dict[str, int] = {}
        self._int_to_id: dict[int, str] = {}
        self._next_int = 0
        self._matrix: np.ndarray | None = None  # numpy backend
        self._index = None
        if self._use_faiss:
            self._index = faiss.IndexFlatIP(dim)

    @property
    def backend(self) -> str:
        return "faiss" if self._use_faiss else "numpy"

    @property
    def size(self) -> int:
        if self._use_faiss and self._index is not None:
            return int(self._index.ntotal)
        if self._matrix is None:
            return 0
        return int(self._matrix.shape[0])

    def upsert(self, ids: Sequence[str], vectors: np.ndarray) -> None:
        vectors = _l2_normalize(vectors)
        if vectors.shape[0] != len(ids):
            raise ValueError("ids and vectors length mismatch")
        if vectors.shape[1] != self.dim:
            raise ValueError(f"expected dim {self.dim}, got {vectors.shape[1]}")

        # Rebuild strategy for simplicity: replace all entries for given ids then add
        # For FlatIP without remove_ids support on all builds, rebuild from scratch
        # when updating existing ids.
        existing = set(self._id_to_int.keys())
        if any(i in existing for i in ids) and self.size > 0:
            keep_ids = [i for i in self._int_to_id.values() if i not in ids]
            if keep_ids:
                keep_vecs = self._vectors_for_ids(keep_ids)
                self._reset()  # dsa:ignore
                self._add_new(keep_ids, keep_vecs)
            else:
                self._reset()  # dsa:ignore
        self._add_new(list(ids), vectors)

    def vectors_for_ids(self, ids: Sequence[str]) -> np.ndarray:
        """Return L2-normalized vectors for the given symbol ids (public export)."""
        rows = []
        for sid in ids:
            idx = self._id_to_int[sid]
            if self._use_faiss:
                # Newer FAISS bindings return a NumPy array; older bindings are
                # safely normalized by asarray as well.
                rows.append(np.asarray(self._index.reconstruct(idx), dtype=np.float32))  # type: ignore[union-attr]
            else:
                assert self._matrix is not None
                rows.append(self._matrix[idx])
        return _l2_normalize(np.stack(rows, axis=0))

    def _vectors_for_ids(self, ids: Sequence[str]) -> np.ndarray:
        return self.vectors_for_ids(ids)

    def export_matrix(self) -> tuple[list[str], np.ndarray]:
        """Return (ids_in_index_order, matrix) for all indexed vectors."""
        if self.size == 0:
            return [], np.zeros((0, self.dim), dtype=np.float32)
        ids = [self._int_to_id[i] for i in sorted(self._int_to_id.keys())]
        return ids, self.vectors_for_ids(ids)

    def _reset(self) -> None:
        self._id_to_int.clear()
        self._int_to_id.clear()
        self._next_int = 0
        self._matrix = None
        if self._use_faiss:
            self._index = faiss.IndexFlatIP(self.dim)

    def _add_new(self, ids: Sequence[str], vectors: np.ndarray) -> None:
        vectors = _l2_normalize(vectors)
        start = self._next_int
        for offset, sid in enumerate(ids):
            iid = start + offset
            self._id_to_int[sid] = iid
            self._int_to_id[iid] = sid
        self._next_int = start + len(ids)
        if self._use_faiss:
            self._index.add(vectors)  # type: ignore[union-attr]
        else:
            if self._matrix is None:
                self._matrix = vectors.copy()
            else:
                self._matrix = np.vstack([self._matrix, vectors])

    def search(self, query: np.ndarray, k: int = 5) -> list[tuple[str, float]]:
        if self.size == 0:
            return []
        q = _l2_normalize(query)
        if q.shape[0] != 1:
            q = q[:1]
        k = min(k, self.size)
        if self._use_faiss:
            scores, indices = self._index.search(q, k)  # type: ignore[union-attr]
            results: list[tuple[str, float]] = []
            for score, idx in zip(scores[0], indices[0], strict=False):
                if idx < 0:
                    continue
                sid = self._int_to_id.get(int(idx))
                if sid is not None:
                    results.append((sid, float(score)))
            return results
        assert self._matrix is not None
        sims = (self._matrix @ q.T).ravel()
        top = np.argsort(-sims)[:k]
        return [(self._int_to_id[int(i)], float(sims[i])) for i in top]

    def save(self, directory: str | Path) -> Path:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        meta = {
            "dim": self.dim,
            "backend": self.backend,
            "id_to_int": self._id_to_int,
            "next_int": self._next_int,
        }
        (directory / "id_map.json").write_text(json.dumps(meta), encoding="utf-8")
        if self._use_faiss:
            faiss.write_index(self._index, str(directory / "index.faiss"))
        else:
            mat = self._matrix if self._matrix is not None else np.zeros((0, self.dim), dtype=np.float32)
            np.save(directory / "vectors.npy", mat)
        return directory

    @classmethod
    def load(cls, directory: str | Path, prefer_faiss: bool | None = None) -> VectorStore:
        directory = Path(directory)
        meta = json.loads((directory / "id_map.json").read_text(encoding="utf-8"))
        dim = int(meta["dim"])
        stored_backend = meta.get("backend", "numpy")
        use_faiss = prefer_faiss
        if use_faiss is None:
            use_faiss = stored_backend == "faiss" and _HAS_FAISS
        store = cls(dim=dim, use_faiss=bool(use_faiss))
        store._id_to_int = {str(k): int(v) for k, v in meta["id_to_int"].items()}  # dsa:ignore
        store._int_to_id = {int(v): str(k) for k, v in store._id_to_int.items()}  # dsa:ignore
        store._next_int = int(meta.get("next_int", len(store._id_to_int)))

        faiss_path = directory / "index.faiss"
        npy_path = directory / "vectors.npy"
        if store._use_faiss and faiss_path.exists():
            store._index = faiss.read_index(str(faiss_path))  # dsa:ignore
        elif npy_path.exists():
            store._use_faiss = False
            store._index = None
            store._matrix = np.load(npy_path).astype(np.float32)
        elif faiss_path.exists() and _HAS_FAISS:
            store._use_faiss = True
            store._index = faiss.read_index(str(faiss_path))  # dsa:ignore
        else:
            raise FileNotFoundError(
                f"WHAT: No vector index found under {directory}.\n"
                "WHY: expected index.faiss or vectors.npy.\n"
                "FIX: rebuild with VectorStore.upsert then save()."
            )
        return store


def default_vectors_dir(repo_path: str) -> Path:
    return Path(repo_path) / ".gdss" / "vectors"


def index_symbols(
    store: VectorStore,
    embeddings: Mapping[str, object],
) -> None:
    """Upsert EmbeddingVector dict into the store."""
    from gdss.embeddings.types import EmbeddingVector

    if not embeddings:
        return
    ids = list(embeddings.keys())
    vecs = []
    for sid in ids:
        emb = embeddings[sid]
        if isinstance(emb, EmbeddingVector):
            vecs.append(emb.vector)
        else:
            vecs.append(np.asarray(emb, dtype=np.float32))
    store.upsert(ids, np.stack(vecs, axis=0))
