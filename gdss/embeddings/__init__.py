"""Probabilistic embedding layer (Layer 6). Assistive only — never imported by core/graph/watcher."""

from gdss.embeddings.branch_vector import (
    aggregate_branch_tip,
    embed_symbols,
    embedding_distance_to_attractor,
)
from gdss.embeddings.cache import EmbeddingCache
from gdss.embeddings.encoder import CodeEncoder, DeterministicBagEncoder, get_encoder
from gdss.embeddings.similarity import cosine_distance, cosine_similarity
from gdss.embeddings.types import BranchTipVector, EmbeddingVector
from gdss.embeddings.vector_store import VectorStore, index_symbols

__all__ = [
    "EmbeddingVector",
    "BranchTipVector",
    "CodeEncoder",
    "DeterministicBagEncoder",
    "get_encoder",
    "cosine_similarity",
    "cosine_distance",
    "EmbeddingCache",
    "VectorStore",
    "index_symbols",
    "embed_symbols",
    "aggregate_branch_tip",
    "embedding_distance_to_attractor",
]
