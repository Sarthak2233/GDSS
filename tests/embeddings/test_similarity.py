import numpy as np

from gdss.embeddings.similarity import cosine_distance, cosine_similarity


def test_cosine_identity():
    v = np.array([1.0, 0.0, 0.0])
    assert np.isclose(float(cosine_similarity(v, v)), 1.0)
    assert np.isclose(float(cosine_distance(v, v)), 0.0)


def test_cosine_orthogonal():
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert np.isclose(float(cosine_similarity(a, b)), 0.0)
    assert np.isclose(float(cosine_distance(a, b)), 1.0)


def test_cosine_batch_matrix():
    a = np.array([[1.0, 0.0], [0.0, 1.0]])
    b = np.array([[1.0, 0.0], [0.0, 1.0]])
    sim = cosine_similarity(a, b)
    assert sim.shape == (2, 2)
    assert np.isclose(sim[0, 0], 1.0)
    assert np.isclose(sim[0, 1], 0.0)
