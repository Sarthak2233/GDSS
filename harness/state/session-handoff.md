# Session Handoff: Frontend hard gates done (F0.1)

## Current State
- `frontend-harness` (F0) — **done**
- `frontend-hard-gates` (F0.1) — **done** (`web/node_modules` via pnpm; F1/F2
  enforce; size-limit runs; Playwright SKIP until `web/e2e/*.spec.ts` exists)
- Remaining `frontend-*` (F1–F10) — **pending**
- Decisions: same queue as backend; **API-first** (`gdss serve` / `gdss/api`
  before live UIs); no CLI scraping.

## 2026-07-27 - 3dsvg skill + rule harness

- Created `.cursor/skills/svg-3d-extrusion/SKILL.md` and `.cursor/rules/frontend/21-svg-3d-extrusion.mdc`.
- Updated `harness/state/feature_list.json` and appended an entry to `harness/state/progress.md` recording the work and verification evidence.
- Frontend verify (F1/F2/F3) ran and reported no regressions.

Next: when ready, pick `frontend-local-api` (F1) or request a small reference component using `3dsvg` to be added under `web/components/ui`.

Backend next unfinished product phase with deps satisfied: `phase4-tensor`.
Frontend next with deps satisfied: none until backend deps for
`frontend-local-api` (`phase1-graph`, `phase2-embeddings`, `phase3-drift` —
already done) — so **`frontend-local-api`** is now unblocked.

## Next Steps (pick ONE)
1. **`frontend-local-api`** (recommended for visual brain) — additive
   `gdss/api/` + `gdss serve` JSON for status/graph/drift/alerts/log/similar.
2. **`phase4-tensor`** — full `Omega_{ij}` conflict tensor (backend track).

## How to resume
```bash
source venv/bin/activate
bash harness/init.sh
bash harness/verify.sh
# Frontend toolchain (already installed locally):
cd web && pnpm install   # if node_modules missing
bash harness/verify-frontend.sh
# Recommended next: frontend-local-api
```
