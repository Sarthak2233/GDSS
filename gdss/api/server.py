"""FastAPI Server for GDSS Local API."""

import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from gdss.api import service
from gdss.api.models import HealthResponse
from gdss.logger import get_logger

logger = get_logger("gdss.api.server")


def create_app(repo_path: Path) -> FastAPI:
    repo_path_str = str(Path(repo_path).resolve())
    app = FastAPI(title="GDSS Local API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
        return {"version": "1.0", "status": "ok", "repo": repo_path_str}

    @app.get("/v1/status")
    def status(ref: str | None = None):
        return format_resp(service.get_status(repo_path_str, ref))

    @app.get("/v1/graph")
    def graph(ref: str | None = None):
        return format_resp(service.get_graph(repo_path_str, ref))

    @app.get("/v1/drift")
    def drift(
        ref: str | None = None,
        branch: str | None = None,
        branches: str | None = None,
        exclude: str | None = None,
    ):
        return format_resp(service.get_drift(repo_path_str, ref, branch, branches, exclude))

    @app.get("/v1/drift/history")
    def drift_history(branch: str, n: int = 20):
        return format_resp(service.get_drift_history(repo_path_str, branch, n))

    @app.get("/v1/alerts")
    def alerts(ref: str | None = None):
        return format_resp(service.get_alerts(repo_path_str, ref))

    @app.get("/v1/log")
    def log(n: int = 20):
        return format_resp(service.get_log(repo_path_str, n))

    @app.get("/v1/similar")
    def similar(symbol: str, k: int = 5):
        return format_resp(service.get_similar(repo_path_str, symbol, k))

    @app.get("/v1/embeddings/projection")
    def embeddings_projection(dims: int = 2, limit: int = 500):
        return format_resp(service.get_embeddings_projection(repo_path_str, dims=dims, limit=limit))

    @app.get("/v1/tensor")
    def tensor(
        ref: str | None = None,
        branches: str | None = None,
        exclude: str | None = None,
        include_remotes: bool = False,
    ):
        return format_resp(
            service.get_tensor(repo_path_str, ref, branches, exclude, include_remotes)
        )

    @app.get("/v1/symbols")
    def symbols(ref: str | None = None):
        return format_resp(service.get_symbols(repo_path_str, ref))

    @app.get("/v1/branches")
    def branches():
        return format_resp(service.get_branches(repo_path_str))

    @app.get("/v1/hierarchy")
    def get_hierarchy():
        return format_resp(service.get_hierarchy(repo_path_str))

    @app.post("/v1/hierarchy")
    async def post_hierarchy(request: Request):
        try:
            body = await request.json()
        except Exception:
            body = {}
        return format_resp(service.update_hierarchy(repo_path_str, body))

    @app.get("/v1/model/status")
    def model_status():
        return format_resp(service.get_model_status())

    @app.get("/v1/suggestions")
    def suggestions(
        request: Request,
        ref: str | None = None,
        format: str = "metadata",
        llm: bool = False,
        combos: int = 3,
        max_candidates: int = 50,
    ):
        if format in {"prompt", "source"}:
            token = request.headers.get("X-GDSS-Local-Token")
            if not getattr(app.state, "allow_local_source", False) and token != getattr(
                app.state, "local_token", ""
            ):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "Source-bearing requests require --allow-local-source or valid X-GDSS-Local-Token"
                    },
                )
        return format_resp(
            service.get_suggestions(repo_path_str, ref, format, llm, combos, max_candidates)
        )

    return app
