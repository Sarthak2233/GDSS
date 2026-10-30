"""CLI-facing helpers: rebuild FAISS index from parsed symbols; find similar."""

from __future__ import annotations

import os
from collections.abc import Sequence

import numpy as np

from gdss.core.ast_parser import SOURCE_EXTENSIONS, ASTParser
from gdss.core.transform_types import CodeSymbol
from gdss.embeddings.branch_vector import embed_symbols
from gdss.embeddings.cache import EmbeddingCache
from gdss.embeddings.encoder import CodeEncoder, get_encoder
from gdss.embeddings.vector_store import VectorStore, default_vectors_dir, index_symbols
from gdss.graph.graph_builder import SKIP_DIR_NAMES
from gdss.logger import get_logger

logger = get_logger("gdss.embeddings.service")


def collect_repo_symbols(repo_path: str, parser: ASTParser | None = None) -> list[CodeSymbol]:
    """Parse supported source files under repo_path into CodeSymbols."""
    parser = parser or ASTParser()
    root_path = os.path.abspath(repo_path)
    symbols: list[CodeSymbol] = []
    for root, dirs, files in os.walk(root_path):
        dirs[:] = [
            name
            for name in dirs
            if name not in SKIP_DIR_NAMES
            and not name.startswith(".")
            and not name.endswith(".egg-info")
        ]
        for filename in files:
            if (
                filename.endswith(".min.js")
                or filename.endswith(".min.css")
                or filename.endswith(".bundle.js")
                or filename.endswith(".chunk.js")
            ):
                continue
            if not filename.endswith(SOURCE_EXTENSIONS):
                continue
            absolute_path = os.path.join(root, filename)
            chart_location = os.path.relpath(absolute_path, root_path)
            try:
                file_syms = parser.parse_file(absolute_path)
            except OSError:
                continue
            for sym in file_syms:
                sym.ensure_identity(chart_location)
                symbols.append(sym)
    return symbols


def rebuild_vector_index(
    repo_path: str,
    encoder: CodeEncoder | None = None,
    symbols: Sequence[CodeSymbol] | None = None,
) -> tuple[VectorStore, int]:
    """Embed symbols and persist VectorStore under .gdss/vectors/."""
    encoder = encoder or get_encoder()
    symbols = list(symbols) if symbols is not None else collect_repo_symbols(repo_path)
    logger.info(
        "Rebuilding vector index for %d symbols using encoder %s", len(symbols), encoder.name
    )
    cache = EmbeddingCache(encoder)
    # embed via cache by batching texts through embed_symbols path
    embeddings = embed_symbols(symbols, encoder)
    # warm cache keys (optional): re-encode through cache for consistency
    _ = cache
    store = VectorStore(dim=encoder.dim)
    index_symbols(store, embeddings)
    out_dir = default_vectors_dir(repo_path)
    store.save(out_dir)
    num_embeddings = len(embeddings)
    logger.info(
        "Vector index persisted to %s (%d vectors, backend=%s)",
        out_dir,
        num_embeddings,
        store.backend,
    )
    return store, num_embeddings


def load_or_build_index(
    repo_path: str,
    encoder: CodeEncoder | None = None,
) -> VectorStore:
    encoder = encoder or get_encoder()
    path = default_vectors_dir(repo_path)
    id_map = path / "id_map.json"
    if id_map.is_file():
        try:
            store = VectorStore.load(path)
            if store.dim == encoder.dim and store.size > 0:
                logger.debug("Loaded existing vector index from %s (%d items)", path, store.size)
                return store
        except Exception as exc:
            logger.debug(
                "Existing vector index at %s could not be loaded (%s), rebuilding...", path, exc
            )
    store, _ = rebuild_vector_index(repo_path, encoder=encoder)
    return store


def find_similar_symbols(
    repo_path: str,
    query_name: str,
    k: int = 5,
    encoder: CodeEncoder | None = None,
) -> list[tuple[str, float, CodeSymbol | None]]:
    """
    Return top-k (symbol_id, score, CodeSymbol|None) neighbors for a symbol name.
    Rebuilds index if missing.
    """
    encoder = encoder or get_encoder()
    symbols = collect_repo_symbols(repo_path)
    by_name = [s for s in symbols if (s.name or "") == query_name]
    if not by_name:
        by_name = [s for s in symbols if (s.name or "").lower() == query_name.lower()]
    if not by_name:
        by_name = [
            s
            for s in symbols
            if query_name.lower() in (s.name or "").lower()
            or query_name.lower() in (s.symbol_id or "").lower()
        ]
    if not by_name:
        return []
    query_sym = by_name[0]
    query_sym.ensure_identity(query_sym.chart_location)
    q_emb = embed_symbols([query_sym], encoder)
    q_vec = next(iter(q_emb.values())).vector

    store = load_or_build_index(repo_path, encoder=encoder)
    # Ensure query symbol is indexed
    all_emb = embed_symbols(symbols, encoder)
    if store.size == 0 or query_sym.symbol_id not in getattr(store, "_id_to_int", {}):
        index_symbols(store, all_emb)
        store.save(default_vectors_dir(repo_path))

    hits = store.search(q_vec, k=k + 1)
    id_to_sym = {s.symbol_id: s for s in symbols}
    results: list[tuple[str, float, CodeSymbol | None]] = []
    for sid, score in hits:
        if query_sym.symbol_id and sid == query_sym.symbol_id:
            continue
        results.append((sid, score, id_to_sym.get(sid)))
        if len(results) >= k:
            break
    return results


def _pca_project(matrix: np.ndarray, dims: int) -> np.ndarray:
    """Project rows of matrix to `dims` via centered SVD PCA. O(n·d·min(n,d))."""
    n, d = matrix.shape
    out_dims = max(1, dims)
    if n == 0:
        return np.zeros((0, out_dims), dtype=np.float32)
    if n == 1 or d == 0:
        return np.zeros((n, out_dims), dtype=np.float32)
    rank = min(out_dims, d, n - 1)
    centered = matrix - matrix.mean(axis=0, keepdims=True)
    _u, _s, vt = np.linalg.svd(centered, full_matrices=False)
    components = vt[:rank].T  # (d, rank)
    projected = centered @ components
    projected_f32 = projected.astype(np.float32)
    if projected_f32.shape[1] < out_dims:
        pad = np.zeros((n, out_dims - projected_f32.shape[1]), dtype=np.float32)
        projected_f32 = np.hstack([projected_f32, pad])
    return projected_f32[:, :out_dims]


def project_symbol_embeddings(
    repo_path: str,
    dims: int = 2,
    limit: int = 500,
    encoder: CodeEncoder | None = None,
) -> dict:
    """
    Build (or load) the vector index and return an assistive PCA projection.

    Returns a dict with assistive metadata and points [{id, name, type, location, x, y, ...}].
    No source bodies. Caps to `limit` symbols (stable order by id).
    """
    encoder = encoder or get_encoder()
    dims = 2 if dims not in {2, 3} else dims
    limit = max(1, min(limit, 2000))

    symbols = collect_repo_symbols(repo_path)
    store = load_or_build_index(repo_path, encoder=encoder)
    if store.size == 0 and symbols:
        embeddings = embed_symbols(symbols, encoder)
        index_symbols(store, embeddings)
        store.save(default_vectors_dir(repo_path))

    ids, matrix = store.export_matrix()
    n_ids = len(ids)
    if n_ids == 0:
        return {
            "assistive": True,
            "method": "pca",
            "dims": dims,
            "encoder": encoder.name,
            "dim_full": encoder.dim,
            "points": [],
        }

    # Stable cap by sorted id for deterministic UI
    order = sorted(range(n_ids), key=lambda i: ids[i])
    if len(order) > limit:
        order = order[:limit]
    capped_ids = [ids[i] for i in order]
    capped = matrix[np.asarray(order, dtype=np.int64)]

    coords = _pca_project(capped, dims)

    id_to_sym = {s.symbol_id: s for s in symbols}
    points = []
    for i, sid in enumerate(capped_ids):
        sym = id_to_sym.get(sid)
        sym_type = "symbol"
        if sym is not None:
            t = sym.type
            sym_type = t.value if hasattr(t, "value") else str(t)
        point: dict = {
            "id": sid,
            "name": (sym.name if sym else sid) or sid,
            "type": sym_type,
            "location": (sym.chart_location or "") if sym else "",
            "x": float(coords[i, 0]) if coords.shape[1] > 0 else 0.0,
            "y": float(coords[i, 1]) if coords.shape[1] > 1 else 0.0,
        }
        if dims >= 3 and coords.shape[1] > 2:
            point["z"] = float(coords[i, 2])
        points.append(point)

    return {
        "assistive": True,
        "method": "pca",
        "dims": dims,
        "encoder": encoder.name,
        "dim_full": encoder.dim,
        "points": points,
    }
