import pytest
from fastapi.testclient import TestClient

from gdss.api.server import create_app


@pytest.fixture
def client(repo_path):
    app = create_app(repo_path)
    return TestClient(app)

def test_health_route(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == "1.0"
    assert data["status"] == "ok"
    assert "repo" in data

def test_branches_route(client):
    response = client.get("/v1/branches")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "branches" in response.json()["data"]

def test_drift_history_route(client):
    response = client.get("/v1/drift/history?branch=master&n=5")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_status_route(client):
    response = client.get("/v1/status?ref=master")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_status_invalid_ref(client):
    response = client.get("/v1/status?ref=nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_REF"

def test_graph_route(client):
    response = client.get("/v1/graph?ref=master")
    assert response.status_code == 200

def test_drift_route(client):
    response = client.get("/v1/drift?ref=master")
    assert response.status_code == 200

def test_alerts_route(client):
    response = client.get("/v1/alerts?ref=master")
    assert response.status_code == 200

def test_log_route(client):
    response = client.get("/v1/log?n=5")
    assert response.status_code == 200

def test_similar_route(client):
    response = client.get("/v1/similar?symbol=function_1")
    assert response.status_code == 200


def test_embeddings_projection_route(client):
    response = client.get("/v1/embeddings/projection?dims=2&limit=50")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["data"]["assistive"] is True
    assert body["data"]["method"] == "pca"
    assert "points" in body["data"]


def test_tensor_route(client):
    response = client.get("/v1/tensor?ref=master")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["data"]["form"] == "flat"
    assert "merge_risk" in body["data"]
    assert "commutativity" in body["data"]


def test_symbols_route(client):
    response = client.get("/v1/symbols")
    assert response.status_code == 200
    assert "symbols" in response.json()["data"]

