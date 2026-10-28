# F1 Local API Contract

## Overview

The `frontend-local-api` (F1) exposes the GDSS graph, embedding, and drift capabilities over a local HTTP interface. It serves as the data boundary for the Next.js frontend (F2+).

**Key Constraints:**
- **Local Only:** Binds only to `127.0.0.1`.
- **Single Repository:** The target repository is provided via CLI (`gdss serve --repo PATH`) when the server starts. Endpoints do **not** accept a repository path query parameter. The frontend shows the served path as read-only.
- **Privacy Boundary (Metadata Only):** Responses NEVER include source file bodies, diff patches, docstrings, commit messages (subjects or bodies), or author identities (names/emails). All data is structurally extracted metadata.

## Standardized Responses

### Success Envelope

Every successful API response (HTTP 200) conforms to the following structure:

```json
{
  "version": "1.0",
  "timestamp": "2026-07-27T00:00:00Z",
  "repo": "/absolute/path/to/repo",
  "status": "ok",
  "data": { ... },
  "warnings": [ ... ]
}
```

### Error Envelope

Errors (HTTP 4xx/5xx) always return WHAT/WHY/FIX details.

## Endpoints

### 1. `GET /health`
- **Purpose:** Local process readiness probe.
- **Response:** `{ version, status, repo }` — `repo` is the path bound at serve time.

### 2. `GET /v1/status`
- **Parameters:** `ref` (optional) — attractor / reference branch.
- **Response `data`:** `active_branch`, `reference`, `remote_sync` (ahead/behind), `committed_operators`, `uncommitted_operators`.

### 3. `GET /v1/graph`
- **Parameters:** `ref` (optional; currently working-tree graph; ref accepted for future branch-scoped builds).
- **Response `data`:** `summary`, `nodes`, `edges`.

### 4. `GET /v1/drift`
- **Parameters:** `ref` (attractor), `branch` (optional single branch).
- **Response `data`:**
  - `reference`
  - `drift[]` per branch:
    - `magnitude`, `tip_distance`, `trajectory_integral`
    - `velocity`
    - `convergence_score` (float in [0, 1])
    - `convergence_label` (`converging` | `diverging` | `stable` from velocity sign)
    - `affected[]` with `id`, `name`, `distance`, `reason`
    - `conflict_probability`: `{ score, reasons[], heuristic: "flat" }` from `ConflictProbabilityEstimator`

### 5. `GET /v1/drift/history`
- **Parameters:** `branch` (required), `n` (optional, default 20).
- **Response `data`:** `{ branch, history: [{ timestamp, magnitude }] }` from SnapshotHistory.

### 6. `GET /v1/alerts`
- **Parameters:** `ref` (optional).
- **Response `data`:** list of `{ branch, severity, message, magnitude, affected[] }` where `message` is the rich DriftAlert text and `severity` is `low|medium|high`.

### 7. `GET /v1/log`
- **Parameters:** `n` (optional, default 20, max 100).
- **Response `data`:** list of `{ sha, timestamp, operators[] }` — no commit message/author.

### 8. `GET /v1/similar`
- **Parameters:** `symbol` (required), `k` (optional).
- **Response `data`:** `{ assistive: true, hits: [...] }`.

### 9. `GET /v1/embeddings/projection`
- **Purpose:** Assistive PCA projection of symbol embeddings for the embedding-space UI (`/similar`).
- **Parameters:** `dims` (optional, `2` or `3`, default `2`), `limit` (optional, default `500`, max `2000`).
- **Response `data`:** `{ assistive: true, method: "pca", dims, encoder, dim_full, points: [{ id, name, type, location, x, y, z? }] }` — metadata only (no source bodies).

### 10. `GET /v1/tensor`
- **Purpose:** Flat pairwise conflict tensor `Ω_ij` (same composition as `gdss tensor`). Deterministic; not geometric `⟨v,P(v)⟩_G`.
- **Parameters:** `ref` (optional, default `main`) — attractor / reference branch.
- **Response `data`:**
  - `reference`, `form: "flat"`
  - `branches: string[]` — matrix axis order
  - `entries: [{ i, j, omega, reasons }]` — sparse non-zero cells
  - `merge_risk` — `R_merge` (sum of stored entry omegas)
  - `commutativity: [{ a, b, class }]` — full `OperatorType×OperatorType` table (`commute`|`interfere`|`independent`)
  - `message` (optional) — when single-attractor / no other branches (HTTP 200 + `warnings`)
- **Honesty:** flat rank-2 pairwise marginal; never auto-merges.

### 11. `GET /v1/symbols`
- **Parameters:** `ref` (optional).
- **Response `data`:** `{ symbols: [{ id, name, type, location }] }`.

### 12. `GET /v1/branches`
- **Purpose:** List local branches for the ref picker dropdown.
- **Response `data`:** `{ branches: string[], active_branch, repo }`.

## Status Codes

- `200 OK`: Successful operation.
- `400 Bad Request`: Invalid parameters.
- `404 Not Found`: Invalid ref or index error.
- `500 Internal Server Error`: Safe WHAT/WHY/FIX only.

## Performance & Content-Addressed In-Memory Caching

To prevent long-running Tree-Sitter AST traversals from blocking the local HTTP event loop during frontend dashboard polling, GDSS leverages Git's cryptographic Merkle DAG immutability:

1. **Commit-SHA Service Memoization (`GET /v1/drift`):**
   - Cache key: `(repo_path, branch, branch_sha, ref, ref_sha)`
   - Because a Git commit SHA permanently identifies the exact state of the source tree, drift calculations between two unchanged commit hashes are mathematically identical.
   - **Performance:** Cold request $\approx 15\text{s} \rightarrow$ subsequent polls $\approx 6\text{ms}$ (**2,700x speedup**).
   - **Invalidation:** Zero-maintenance. As soon as a developer pushes or creates a commit, `branch_sha` advances, automatically triggering fresh analysis.

2. **Commit-Level Symbol & Tip Vector Caching (`DriftEngine`):**
   - `DriftEngine` caches parsed symbol lists (`_COMMIT_SYMBOLS_CACHE`) and tip vectors (`_TIP_VECTOR_CACHE`) keyed by immutable `commit_sha`.
   - When evaluating trajectory path integrals ($I(B_i)$) across historical commits, each historical commit is parsed at most once in memory.

3. **Client Polling & Timeout Contracts:**
   - **Axios Timeout:** 60 seconds (`timeout: 60000`) in `web/lib/api.ts` to accommodate cold multi-branch AST analysis on large repositories.
   - **Polling Interval:** 30 seconds (`refetchInterval: 30000`) in `DashboardGrid` to ensure polling does not outpace server computation.

## CLI

```bash
gdss serve --repo PATH --port 8787
```

Frontend: `NEXT_PUBLIC_GDSS_API` (e.g. `http://127.0.0.1:8787`).
