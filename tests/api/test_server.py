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
    assert response.json() == {"version": "1.0", "status": "ok"}

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
