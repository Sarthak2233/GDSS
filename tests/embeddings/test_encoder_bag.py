"""Deterministic bag encoder and content-hash LRU cache."""

import numpy as np

from gdss.embeddings.encoder import DeterministicBagEncoder, get_encoder
from gdss.embeddings.cache import EmbeddingCache


def test_bag_encoder_stable_and_batched():
    enc = DeterministicBagEncoder(dim=384)
    texts = ["def foo():\n    return 1", "def bar():\n    pass"]
    a = enc.encode_texts(texts)
    b = enc.encode_texts(texts)
    assert a.shape == (2, 384)
    assert np.allclose(a, b)
    # Different texts should not be identical vectors
    assert not np.allclose(a[0], a[1])


def test_bag_encoder_l2_normalized():
    enc = DeterministicBagEncoder(dim=384)
    vecs = enc.encode_texts(["hello world"])
    norms = np.linalg.norm(vecs, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5)


def test_get_encoder_defaults_to_bag():
    enc = get_encoder()
    assert isinstance(enc, DeterministicBagEncoder)


def test_content_hash_cache_avoids_reencode():
    enc = DeterministicBagEncoder(dim=64)
    calls = {"n": 0}
    original = enc.encode_texts

    def counting(texts):
        calls["n"] += 1
        return original(texts)

    enc.encode_texts = counting  # type: ignore[method-assign]
    cache = EmbeddingCache(enc, max_size=32)
    t = ["alpha beta", "gamma"]
    first = cache.encode(t)
    second = cache.encode(t)
    assert np.allclose(first, second)
    assert calls["n"] == 1  # second call fully cache-hit
