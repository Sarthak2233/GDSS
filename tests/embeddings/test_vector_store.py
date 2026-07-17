"""FAISS / numpy VectorStore round-trips."""

import numpy as np
import pytest

from gdss.embeddings.encoder import DeterministicBagEncoder
from gdss.embeddings.vector_store import VectorStore, index_symbols
from gdss.embeddings.types import EmbeddingVector


@pytest.fixture(params=[False, True])
def store_backend(request):
    use_faiss = request.param
    if use_faiss:
        faiss = pytest.importorskip("faiss")
        _ = faiss  # silence unused
    return use_faiss


def test_upsert_search_self_match(store_backend, tmp_path):
    enc = DeterministicBagEncoder(dim=32)
    texts = ["payment processor charge", "unrelated hello world"]
    vecs = enc.encode_texts(texts)
    store = VectorStore(dim=32, use_faiss=store_backend)
    store.upsert(["pay", "hello"], vecs)
    hits = store.search(vecs[0], k=1)
    assert hits[0][0] == "pay"
    assert hits[0][1] > 0.9


def test_save_load_roundtrip(store_backend, tmp_path):
    enc = DeterministicBagEncoder(dim=32)
    vecs = enc.encode_texts(["alpha", "beta"])
    store = VectorStore(dim=32, use_faiss=store_backend)
    store.upsert(["a", "b"], vecs)
    out = tmp_path / "vectors"
    store.save(out)
    loaded = VectorStore.load(out, prefer_faiss=store_backend)
    hits = loaded.search(vecs[1], k=1)
    assert hits[0][0] == "b"


def test_index_symbols_helper():
    enc = DeterministicBagEncoder(dim=16)
    v = enc.encode_texts(["x"])[0]
    emb = {"sym1": EmbeddingVector(vector=v, dim=16, source_id="sym1")}
    store = VectorStore(dim=16, use_faiss=False)
    index_symbols(store, emb)
    assert store.size == 1
