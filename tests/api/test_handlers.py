from gdss.api.service import (
    get_alerts,
    get_drift,
    get_embeddings_projection,
    get_graph,
    get_log,
    get_similar,
    get_status,
    get_symbols,
    get_tensor,
)
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

def test_get_drift_convergence_score_and_label(divergent_repo):
    """convergence_score is float; convergence_label is converging|diverging|stable."""
    repo_path, base_name = divergent_repo
    response = get_drift(repo_path, ref=base_name)
    assert response["status"] == "ok"
    drift = response["data"]["drift"]
    assert drift, "expected at least one non-reference branch"
    row = drift[0]
    assert isinstance(row["convergence_score"], float)
    assert 0.0 <= row["convergence_score"] <= 1.0
    assert row["convergence_label"] in {"converging", "diverging", "stable"}
    assert isinstance(row["tip_distance"], float)
    assert isinstance(row["trajectory_integral"], float)
    cp = row["conflict_probability"]
    assert 0.0 <= cp["score"] <= 1.0
    assert isinstance(cp["reasons"], list)
    assert cp["heuristic"] == "flat"

def test_get_alerts_safe(divergent_repo):
    repo_path, base_name = divergent_repo
    response = get_alerts(repo_path, ref=base_name)
    assert response["status"] == "ok"
    assert_privacy_safe(response)

def test_serialize_alert_uses_rich_message():
    """Alert serialization uses DriftAlert.message and severity string."""
    from gdss.api.service import _serialize_alert
    from gdss.drift.types import AffectedSymbol, DriftAlert

    alert = DriftAlert(
        severity="high",
        branch="feature",
        reference_branch="main",
        magnitude=0.9,
        message="HIGH DRIFT ALERT\n\nfeature diverging from main\nMagnitude: 0.900\n",
        affected=(
            AffectedSymbol(
                symbol_id="a::fn",
                name="fn",
                distance=0.4,
                reason="modified_in_both",
            ),
        ),
        timestamp=1.0,
    )
    row = _serialize_alert(alert)
    assert row["severity"] == "high"
    assert "Magnitude:" in row["message"]
    assert "feature" in row["message"]
    assert "DriftAlert(" not in row["message"]
    assert row["affected"][0]["distance"] == 0.4
    assert row["affected"][0]["reason"] == "modified_in_both"

def test_get_alerts_message_is_rich(divergent_repo):
    """Alert message uses DriftAlert.message when alerts fire."""
    repo_path, base_name = divergent_repo
    # Force low thresholds so the divergent fixture produces alerts
    from unittest.mock import patch

    from gdss.drift.alerts import DriftAlerts

    with patch(
        "gdss.api.service.DriftAlerts",
        lambda: DriftAlerts(thresholds={"low": 0.0, "medium": 0.01, "high": 0.5}),
    ):
        response = get_alerts(repo_path, ref=base_name)
    assert response["status"] == "ok"
    alerts = response["data"]
    assert alerts, "expected alerts with lowered thresholds"
    alert = alerts[0]
    assert isinstance(alert["severity"], str)
    assert alert["severity"] in {"low", "medium", "high"}
    assert "Magnitude:" in alert["message"]
    assert alert["branch"] in alert["message"]
    assert "DriftAlert(" not in alert["message"]
    for sym in alert["affected"]:
        assert "id" in sym and "name" in sym
        assert "distance" in sym
        assert "reason" in sym

def test_get_branches(divergent_repo):
    from gdss.api.service import get_branches

    repo_path, base_name = divergent_repo
    response = get_branches(repo_path)
    assert response["status"] == "ok"
    assert base_name in response["data"]["branches"]
    assert "feature" in response["data"]["branches"]
    assert response["data"]["active_branch"] is not None

def test_get_drift_history(divergent_repo):
    from gdss.api.service import get_drift_history

    repo_path, base_name = divergent_repo
    # Populate history via a drift snapshot
    get_drift(repo_path, ref=base_name, branch="feature")
    response = get_drift_history(repo_path, branch="feature", n=5)
    assert response["status"] == "ok"
    assert response["data"]["branch"] == "feature"
    assert len(response["data"]["history"]) >= 1
    assert "timestamp" in response["data"]["history"][0]
    assert "magnitude" in response["data"]["history"][0]

def test_get_log_safe(repo_path):
    response = get_log(repo_path, n=5)
    assert response["status"] == "ok"
    assert_privacy_safe(response)

def test_get_similar_safe(repo_path):
    response = get_similar(repo_path, symbol="function_1", k=2)
    assert response["status"] == "ok"
    assert_privacy_safe(response)


def test_get_embeddings_projection_pca_points(repo_path):
    """Assistive PCA projection returns 2D coords and metadata (no source bodies)."""
    response = get_embeddings_projection(repo_path, dims=2, limit=500)
    assert response["status"] == "ok"
    data = response["data"]
    assert data["assistive"] is True
    assert data["method"] == "pca"
    assert data["dims"] == 2
    assert data["encoder"] in {"bag", "onnx"}
    assert isinstance(data["dim_full"], int) and data["dim_full"] > 0
    assert isinstance(data["points"], list)
    assert len(data["points"]) >= 1
    point = data["points"][0]
    for key in ("id", "name", "type", "location", "x", "y"):
        assert key in point
    assert isinstance(point["x"], float)
    assert isinstance(point["y"], float)
    assert_privacy_safe(response)


def test_get_embeddings_projection_respects_limit(repo_path):
    response = get_embeddings_projection(repo_path, dims=2, limit=1)
    assert response["status"] == "ok"
    assert len(response["data"]["points"]) <= 1


def test_get_symbols_safe(repo_path):
    response = get_symbols(repo_path)
    assert response["status"] == "ok"
    assert "symbols" in response["data"]
    assert_privacy_safe(response)


def test_get_tensor_flat_omega_divergent(divergent_repo):
    """Flat Omega matrix + R_merge + commutativity table for multi-branch repo."""
    repo_path, base_name = divergent_repo
    response = get_tensor(repo_path, ref=base_name)
    assert response["status"] == "ok"
    data = response["data"]
    assert data["form"] == "flat"
    assert data["reference"] == base_name
    assert "feature" in data["branches"] or base_name in data["branches"]
    assert isinstance(data["entries"], list)
    assert isinstance(data["merge_risk"], float)
    assert data["merge_risk"] >= 0.0
    assert isinstance(data["commutativity"], list)
    assert len(data["commutativity"]) >= 1
    row = data["commutativity"][0]
    assert "a" in row and "b" in row and "class" in row
    assert_privacy_safe(response)


def test_get_tensor_single_attractor_empty(repo_path):
    """Single-branch repo returns ok with empty matrix and warning."""
    import git

    ref = git.Repo(repo_path).active_branch.name
    response = get_tensor(repo_path, ref=ref)
    assert response["status"] == "ok"
    data = response["data"]
    assert data["form"] == "flat"
    assert data["entries"] == []
    assert data["merge_risk"] == 0.0
    assert response.get("warnings") or data.get("message")


def test_get_drift_includes_history(divergent_repo):
    """GET /v1/drift regulates recent trajectory history in each branch drift row."""
    repo_path, base_name = divergent_repo
    response = get_drift(repo_path, ref=base_name, branch="feature")
    assert response["status"] == "ok"
    drift = response["data"]["drift"]
    assert drift, "expected at least one branch drift row"
    row = drift[0]
    assert "history" in row
    assert isinstance(row["history"], list)
    if row["history"]:
        point = row["history"][0]
        assert "timestamp" in point and "magnitude" in point


def test_get_tensor_excludes_reference_attractor_from_branches(divergent_repo):
    """Conflict tensor Omega_ij matrix axes exclude the reference attractor when divergent branches exist."""
    repo_path, base_name = divergent_repo
    response = get_tensor(repo_path, ref=base_name)
    assert response["status"] == "ok"
    data = response["data"]
    assert "feature" in data["branches"]
    assert base_name not in data["branches"], "Attractor reference branch should not be an axis of the conflict tensor"


def test_convergence_label_deadzone():
    """Tiny velocity noise within 1e-6 per second should be labeled stable."""
    from gdss.api.service import _convergence_label

    assert _convergence_label(1e-8) == "stable"
    assert _convergence_label(-1e-8) == "stable"
    assert _convergence_label(1e-5) == "diverging"
    assert _convergence_label(-1e-5) == "converging"

