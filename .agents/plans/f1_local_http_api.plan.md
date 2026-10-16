# Plan: F1 Local HTTP API

**TL;DR:** Implement `frontend-local-api` as a local, single-repository FastAPI service. `gdss serve --repo PATH --port 8787` binds to `127.0.0.1` and exposes versioned, metadata-only JSON endpoints that wrap already-complete graph, embedding, and drift capabilities. The API omits source text, docstrings, commit subjects/bodies, and author identity. It unlocks the frontend app shell (F2) without coupling the UI to Rich CLI output.

## Scope

**Included:** additive `gdss/api/`, FastAPI/Uvicorn dependencies, `gdss serve`, six V1 routes, strict response DTOs, handler/integration/privacy tests, API smoke coverage, and state/progress updates.

**Excluded:** frontend routes/components, remote/SaaS hosting, authentication, telemetry, multi-repository routing, CORS for non-local origins, conflict-tensor/AI/validation endpoints, and source/diff content. Those belong to later phases.

## Decisions

- **Framework:** FastAPI + Uvicorn.
- **Repository model:** the CLI-required `--repo PATH` is canonical and fixed for one server lifetime; endpoints must not accept a per-request `repo` path.
- **Binding:** `127.0.0.1` by default; do not bind externally in F1.
- **Privacy:** strict metadata only. No source bodies, docstrings, raw diffs, commit subjects/bodies, developer names, emails, or author hashes.
- **Response convention:** every success response has `version`, UTC `timestamp`, configured `repo` identity, `status: "ok"`, `data`, and `warnings`; errors use an HTTP status plus a WHAT/WHY/FIX error envelope.
- **Reference selection:** `ref` is optional where meaningful. Invalid refs return a deterministic client error rather than silently falling back to `main`.
- **CORS:** omit permissive CORS configuration in F1. A same-machine Next.js app may be configured later with a narrow development origin only.

## Steps

### Phase A — Contracts and safety tests

1. **Mark F1 in progress and establish the API contract**
   - Change `frontend-local-api` in `harness/state/feature_list.json` from `pending` to `in_progress`.
   - Add API-specific contract documentation under `docs/` that defines query parameters, response schemas, warning semantics, status codes, and the metadata-only privacy boundary.
   - Establish a single error representation with stable machine-readable `code` plus `details.what`, `details.why`, and `details.fix`.

2. **Write failing privacy and handler tests first**
   - Create `tests/api/` with real temporary Git repositories following the fixtures in `tests/cli/test_status_honesty.py` and `tests/cli/test_drift_cli.py`; do not mock GDSS modules.
   - Add a recursive payload-safety assertion that rejects forbidden response keys/values: source body, docstring, diff/patch, commit message, author name, and email.
   - Add one narrow failing test at a time for each pure handler before implementing it.
   - Add FastAPI `TestClient` route tests to validate success/error status codes, query validation, privacy-safe serialization, and invalid-ref behavior.

### Phase B — API foundation

3. **Add runtime dependencies and the API package**
   - Add `fastapi` and `uvicorn[standard]` to the primary dependencies in `pyproject.toml`; FastAPI is appropriate because `gdss.api` is already an architecture-fitness entrypoint and can legally compose all lower layers.
   - Create additive `gdss/api/__init__.py`, `gdss/api/models.py`, `gdss/api/service.py`, and `gdss/api/server.py`.
   - In `models.py`, define Pydantic request/query and response models. Only whitelist metadata fields; never serialize backend objects with generic `model_dump`, `vars`, or `__dict__`.
   - In `service.py`, place deterministic adapters that transform backend values into safe DTO dictionaries. Keep them independent of FastAPI request/response objects so they can be directly unit tested.
   - In `server.py`, implement `create_app(repo_path: Path) -> FastAPI`, health metadata, exception mapping, and route registration. Resolve/canonicalize the configured repo once and verify it is a Git repo before serving.

4. **Create the command-line server entrypoint** *(depends on 3)*
   - Add `gdss serve --repo PATH --port 8787` to `gdss/cli/main.py`.
   - Validate the repo path before launching Uvicorn, pass the canonical path into `create_app`, bind host to `127.0.0.1`, and report a concise local URL.
   - Preserve existing CLI commands and the interactive shell behavior.

### Phase C — V1 endpoint implementation

5. **Implement `GET /v1/status`** *(depends on 3)*
   - Use `GitObserver` to obtain active branch, reference/merge-base information, ahead/behind state, and working-tree file status.
   - Reuse `extract_trajectory_operators` / `TransformExtractor` to report committed and uncommitted semantic operations.
   - Serialize only operator type, safe file-relative path, symbol id/name, rename endpoints, and changed-block count. Never include symbol body, patch, or commit metadata.
   - Support `ref` as an optional query parameter and return a client error with valid branch names when invalid.

6. **Implement `GET /v1/graph`** *(depends on 3; parallel with 5, 7–10)*
   - Reuse `build_code_graph_from_repo` and the existing JSON-export shape. If its public return shape is not directly usable, add the smallest additive public `CodeGraph` snapshot/serialization helper rather than reconstructing graph internals in the API layer.
   - Return graph summary, nodes (stable id, safe name/type, relative file/chart location), and edges (source, target, relationship). Exclude body, docstring, and implementation-level attributes.
   - Return empty arrays plus warnings for an empty/unsupported repository; do not make lack of supported files a server failure.

7. **Implement `GET /v1/drift` and `GET /v1/alerts`** *(depends on 3; parallel with 5, 6, 8–10)*
   - Reuse `DriftEngine.snapshot`, `SnapshotHistory`, `DriftAlerts`, and `ConflictProbabilityEstimator` where already exposed by the existing CLI behavior.
   - `/v1/drift` returns the reference branch and per-branch magnitude components, velocity, convergence, and privacy-safe affected-symbol metadata.
   - `/v1/alerts` returns severity, branch, magnitude, safe affected symbol names/ids, and generated alert wording; omit any source-derived text.
   - Preserve the backend’s honesty boundary: the current conflict value is heuristic probability, not a completed $\Omega_{ij}$ tensor.

8. **Implement `GET /v1/log`** *(depends on 3; parallel with 5–7, 9–10)*
   - Support bounded `n` with explicit validation and a conservative maximum.
   - Traverse commits using `GitObserver` and derive semantic operators with the existing transform-extraction path.
   - Return commit SHA and safe timestamp only; omit message, body, author, and email. Return safe semantic operation metadata per commit.

9. **Implement `GET /v1/similar`** *(depends on 3; parallel with 5–8, 10)*
   - Require `symbol` and support a validated bounded `k` query parameter.
   - Reuse `find_similar_symbols`; preserve existing index rebuild/loading behavior rather than duplicating vector-store logic.
   - Return stable symbol ids, safe names/locations, similarity scores, index backend metadata, and an explicit `assistive: true` marker/warning so no frontend treats results as deterministic truth.
   - Map missing symbols/indexes to documented client errors with WHAT/WHY/FIX guidance.

10. **Add API metadata and error behavior** *(depends on 5–9)*
   - Add `GET /health` for local process readiness, separate from the V1 product contract.
   - Convert Git path/ref errors, unsupported input, missing symbols, and internal exceptions into the defined envelope. Do not expose stack traces, filesystem paths outside the configured repo, or raw exception details.
   - Ensure paths returned to the browser are relative to the configured repository.

### Phase D — End-to-end confidence and harness state

11. **Add Layer 3 API smoke coverage** *(depends on 4–10)*
   - Add `harness/sensors/api_smoke.sh` or extend the current Layer 3 CLI smoke sensor.
   - Create a temporary Git fixture, launch `gdss serve` on a dynamically selected local port, wait for `/health`, request all six routes, assert JSON and absence of forbidden source/PII patterns, then reliably terminate the server with a shell trap.
   - Wire the sensor into `harness/verify.sh` after existing CLI smoke so it runs in the established end-to-end layer.

12. **Verify and record completion** *(depends on 1–11)*
   - Run `bash harness/init.sh`.
   - Run targeted API tests, then `bash harness/verify.sh`, and `bash harness/verify-frontend.sh` because F1 is a frontend product phase.
   - Update F1 in `harness/state/feature_list.json` to `done` only after all gates pass; record exact evidence in `harness/state/progress.md` and write a clean handoff in `harness/state/session-handoff.md`.

## V1 endpoint contract

| Route | Parameters | Safe `data` payload |
| --- | --- | --- |
| `GET /health` | — | API version, configured local readiness |
| `GET /v1/status` | `ref?` | attractor/ref identity, branch state, ahead/behind, safe committed/uncommitted semantic operators |
| `GET /v1/graph` | `ref?`, optional safe filters | summary, safe nodes, safe edges, warnings/skipped counts |
| `GET /v1/drift` | `ref?`, `branch?` | safe per-branch drift components, velocity, convergence, affected-symbol metadata |
| `GET /v1/alerts` | `ref?` | severity bucket, generated message, magnitude, affected-symbol metadata |
| `GET /v1/log` | `n=20` | SHA, timestamp, privacy-safe semantic operation metadata; no commit text/author |
| `GET /v1/similar` | `symbol` required, `k=5` | assistive neighbor id/name/location/score and index metadata |

## Relevant files

- `pyproject.toml` — add FastAPI/Uvicorn runtime dependencies.
- `gdss/api/__init__.py` *(new)* — API package marker.
- `gdss/api/models.py` *(new)* — strict Pydantic API DTOs and error models.
- `gdss/api/service.py` *(new)* — framework-independent safe data adapters.
- `gdss/api/server.py` *(new)* — `create_app()` and route wiring.
- `gdss/cli/main.py` — add `serve` command only.
- `gdss/graph/code_graph.py` — only if a minimal public snapshot/serializer is required by the existing export path.
- `tests/api/conftest.py` *(new)* — real temporary Git fixture helpers.
- `tests/api/test_privacy.py` *(new)* — forbidden-content guarantees.
- `tests/api/test_handlers.py` *(new)* — one behavior test per adapter.
- `tests/api/test_server.py` *(new)* — `TestClient` route contract tests.
- `harness/sensors/api_smoke.sh` *(new, preferred)* — process-level API smoke sensor.
- `harness/verify.sh` — invoke the API smoke in Layer 3.
- `harness/state/feature_list.json`, `harness/state/progress.md`, `harness/state/session-handoff.md` — lifecycle status/evidence.

## Verification

1. Targeted test sequence: `python -m pytest tests/api -q` then the existing backend tests.
2. Contract coverage: every V1 route returns the standard success envelope; invalid query/ref/symbol cases return the documented WHAT/WHY/FIX error envelope and status.
3. Privacy coverage: every endpoint’s JSON passes the recursive forbidden-field/content guard; tests use identifiers, docstrings, commit text, and author metadata deliberately placed in fixture content to prove they never escape.
4. Local security coverage: requests cannot substitute another repository; server defaults to `127.0.0.1`.
5. Process coverage: `gdss serve --repo FIXTURE --port PORT`, `/health`, all six endpoints, clean shutdown.
6. Full definition of done: `bash harness/verify.sh` and `bash harness/verify-frontend.sh` exit 0. Do not mark F1 done if ruff/mypy sensors are skipped due to a missing backend toolchain; record the environmental skip explicitly.
