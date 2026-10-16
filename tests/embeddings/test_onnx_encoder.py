"""ONNX encoder availability and factory behavior."""

import os

import pytest

from gdss.embeddings.encoder import DeterministicBagEncoder, get_encoder


def test_get_encoder_bag_by_default(monkeypatch):
    monkeypatch.delenv("GDSS_EMBEDDING_BACKEND", raising=False)
    enc = get_encoder()
    assert isinstance(enc, DeterministicBagEncoder)
    assert enc.name == "bag"


def test_get_encoder_onnx_fails_clearly_without_model(monkeypatch, tmp_path):
    monkeypatch.setenv("GDSS_EMBEDDING_BACKEND", "onnx")
    monkeypatch.setenv("GDSS_ONNX_MODEL", str(tmp_path / "missing.onnx"))
    with pytest.raises(RuntimeError) as exc:
        get_encoder(backend="onnx")
    msg = str(exc.value)
    assert "WHAT:" in msg
    assert "FIX:" in msg


@pytest.mark.integration
def test_onnx_encode_if_model_present():
    path = os.environ.get("GDSS_ONNX_MODEL", ".gdss/models/all-MiniLM-L6-v2.onnx")
    if not os.path.isfile(path):
        pytest.skip("ONNX model not present")
    pytest.importorskip("onnxruntime")
    from gdss.embeddings.onnx_encoder import OnnxMiniLMEncoder

    enc = OnnxMiniLMEncoder(model_path=path)
    vecs = enc.encode_texts(["hello world", "payment charge"])
    assert vecs.shape[0] == 2
    assert vecs.shape[1] > 0
