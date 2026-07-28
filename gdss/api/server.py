"""FastAPI Server for GDSS Local API."""
import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from gdss.api import service
from gdss.api.models import HealthResponse

def create_app(repo_path: Path) -> FastAPI:
    repo_path_str = str(Path(repo_path).resolve())
    app = FastAPI(title="GDSS Local API")

    def format_resp(resp: dict) -> dict | JSONResponse:
        if resp.get("status") == "error":
            code = resp["error"]["code"]
            status_code = 404 if "INVALID_REF" in code or "INDEX_ERROR" in code else 400
            return JSONResponse(status_code=status_code, content=resp)
        resp["version"] = "1.0"
        resp["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z"
        resp["repo"] = repo_path_str
        return resp

    @app.get("/health", response_model=HealthResponse)
    def health():
        return {"version": "1.0", "status": "ok"}

    @app.get("/v1/status")
    def status(ref: str | None = None):
        return format_resp(service.get_status(repo_path_str, ref))

    @app.get("/v1/graph")
    def graph(ref: str | None = None):
        return format_resp(service.get_graph(repo_path_str, ref))

    @app.get("/v1/drift")
    def drift(ref: str | None = None, branch: str | None = None):
        return format_resp(service.get_drift(repo_path_str, ref, branch))

    @app.get("/v1/alerts")
    def alerts(ref: str | None = None):
        return format_resp(service.get_alerts(repo_path_str, ref))

    @app.get("/v1/log")
    def log(n: int = 20):
        return format_resp(service.get_log(repo_path_str, n))

    @app.get("/v1/similar")
    def similar(symbol: str, k: int = 5):
        return format_resp(service.get_similar(repo_path_str, symbol, k))

    return app
