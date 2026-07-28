import pytest
from gdss.api.service import get_status, get_graph, get_drift, get_alerts, get_log, get_similar
from tests.api.test_privacy import assert_privacy_safe

def test_get_status_safe(repo_path):
    response = get_status(repo_path)
    assert response["status"] == "ok"
    assert "data" in response
    assert_privacy_safe(response)

def test_get_status_invalid_ref(repo_path):
    response = get_status(repo_path, ref="nonexistent")
    assert response["status"] == "error"
    assert response["error"]["code"] == "INVALID_REF"

def test_get_graph_safe(repo_path):
    response = get_graph(repo_path)
    assert response["status"] == "ok"
    assert_privacy_safe(response)

def test_get_drift_safe(divergent_repo):
    repo_path, base_name = divergent_repo
    response = get_drift(repo_path, ref=base_name)
    assert response["status"] == "ok"
    assert_privacy_safe(response)

def test_get_alerts_safe(divergent_repo):
    repo_path, base_name = divergent_repo
    response = get_alerts(repo_path, ref=base_name)
    assert response["status"] == "ok"
    assert_privacy_safe(response)

def test_get_log_safe(repo_path):
    response = get_log(repo_path, n=5)
    assert response["status"] == "ok"
    assert_privacy_safe(response)

def test_get_similar_safe(repo_path):
    response = get_similar(repo_path, symbol="function_1", k=2)
    assert response["status"] == "ok"
    assert_privacy_safe(response)
