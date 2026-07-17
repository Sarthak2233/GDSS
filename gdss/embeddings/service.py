"""CLI-facing helpers: rebuild FAISS index from parsed symbols; find similar."""

from __future__ import annotations

import os
from collections.abc import Sequence

from gdss.core.ast_parser import SOURCE_EXTENSIONS, ASTParser
from gdss.core.transform_types import CodeSymbol
from gdss.embeddings.branch_vector import embed_symbols
from gdss.embeddings.cache import EmbeddingCache
from gdss.embeddings.encoder import CodeEncoder, get_encoder
from gdss.embeddings.vector_store import VectorStore, default_vectors_dir, index_symbols
from gdss.graph.graph_builder import SKIP_DIR_NAMES


def collect_repo_symbols(repo_path: str, parser: ASTParser | None = None) -> list[CodeSymbol]:
    """Parse supported source files under repo_path into CodeSymbols."""
    parser = parser or ASTParser()
    root_path = os.path.abspath(repo_path)
    symbols: list[CodeSymbol] = []
    for root, dirs, files in os.walk(root_path):
        dirs[:] = [name for name in dirs if name not in SKIP_DIR_NAMES]
        for filename in files:
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
    cache = EmbeddingCache(encoder)
    # embed via cache by batching texts through embed_symbols path
    embeddings = embed_symbols(symbols, encoder)
    # warm cache keys (optional): re-encode through cache for consistency
    _ = cache
    store = VectorStore(dim=encoder.dim)
    index_symbols(store, embeddings)
    store.save(default_vectors_dir(repo_path))
    return store, len(embeddings)


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
                return store
        except Exception:
            pass
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
    by_name = [s for s in symbols if s.name == query_name]
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
