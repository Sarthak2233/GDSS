# F1 Local API Contract

## Overview

The `frontend-local-api` (F1) exposes the GDSS graph, embedding, and drift capabilities over a local HTTP interface. It serves as the data boundary for the Next.js frontend (F2+).

**Key Constraints:**
- **Local Only:** Binds only to `127.0.0.1`.
- **Single Repository:** The target repository is provided via CLI (`--repo`) when the server starts. Endpoints do not accept a repository path.
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

- `data`: The endpoint-specific response payload.
- `warnings`: Array of strings for non-fatal issues (e.g., "Feature XYZ disabled due to missing dependencies").

### Error Envelope

Errors (HTTP 4xx/5xx) always return the following uniform error schema, aligning with the harness's WHAT/WHY/FIX ideology:

```json
{
  "error": {
    "code": "INVALID_REF",
    "details": {
      "what": "The requested Git reference 'feature-x' does not exist.",
      "why": "The local API requires a valid Git branch or tag name to perform traversal analysis.",
      "fix": "Use a valid branch name (e.g., 'main') or omit the 'ref' parameter to use the default."
    }
  }
}
```

## Endpoints

### 1. `GET /health`
- **Purpose:** Local process readiness probe.
- **Parameters:** None.
- **Response `data`:** API version and configured local readiness.

### 2. `GET /v1/status`
- **Purpose:** Get current branch state, ahead/behind trajectory, and committed/uncommitted semantic operators.
- **Parameters:**
  - `ref` (optional string): Target branch or ref. Fallback behavior or explicit errors applied if invalid.
- **Response `data`:**
  - Branch identity
  - Ahead/behind counts
  - Privacy-safe uncommitted and committed semantic operators (type, relative file path, safe symbol ID/name/rename endpoints, changed-block count).

### 3. `GET /v1/graph`
- **Purpose:** Obtain dependency graph nodes and edges.
- **Parameters:**
  - `ref` (optional string): Reference branch context.
- **Response `data`:**
  - `summary`: Graph statistics.
  - `nodes`: Safe metadata (stable ID, safe name/type, relative location).
  - `edges`: Source, target, relationship type.

### 4. `GET /v1/drift`
- **Purpose:** Get calculated drift vectors across active branches against the reference.
- **Parameters:**
  - `ref` (optional string): The reference branch (attractor).
  - `branch` (optional string): Limit drift calc to a specific branch.
- **Response `data`:**
  - Reference branch name.
  - Per-branch magnitude, velocity, and convergence.
  - Privacy-safe affected symbol IDs and names.

### 5. `GET /v1/alerts`
- **Purpose:** Retrieve generated conflict severity warnings.
- **Parameters:**
  - `ref` (optional string): The reference branch.
- **Response `data`:**
  - Alert severity bucket.
  - Generated explanation (omitting source text).
  - Magnitude value.
  - Formatted safe affected-symbol metadata.

### 6. `GET /v1/log`
- **Purpose:** Linear metadata-only commit history with extracted semantic operations.
- **Parameters:**
  - `n` (optional integer): Bounded number of commits (default: 20). Maximum bounded limit enforced by server.
- **Response `data`:**
  - List of commits containing: SHA, UTC timestamp, and semantic operation metadata arrays (excluding message/author).

### 7. `GET /v1/similar`
- **Purpose:** Assistive vector similarity search for symbols.
- **Parameters:**
  - `symbol` (required string): Query symbol identifier.
  - `k` (optional integer): Number of neighbors to return (default: 5).
- **Response `data`:**
  - Stable symbol IDs, names, locations, and scores.
  - Index metadata.
  - Contains explicit `"assistive": true` flag to indicate non-deterministic confidence.

## Status Codes

- `200 OK`: Successful operation.
- `400 Bad Request`: Invalid parameters (e.g., `k` out of bounds, missing required `symbol` parameter).
- `404 Not Found`: Specific branch (`INVALID_REF`) or symbol not found.
- `500 Internal Server Error`: For unhandled invariants; stack traces are suppressed and safe WHAT/WHY/FIX is presented.
