# GDSS Harness

This folder, together with `AGENTS.md` and `.cursor/`, is the **harness** for
GDSS: the engineered environment that lets AI coding agents extend this project
safely and reliably. It does not change GDSS's behavior; it governs how changes
are made.

> Agent = Model + Harness. The model decides what code to write. The harness
> governs when, where, and how - and whether the result is actually done.

The design follows *harness engineering*
(guides + sensors),  *five subsystems*, and concrete sensor
patterns from skills.

## The two controls

- **Guides (feedforward)** - steer the agent *before* it acts. Increase the odds
  of getting it right the first time.
- **Sensors (feedback)** - validate *after* it acts. Catch what slipped through,
  with messages written for agents (WHAT / WHY / FIX).

Each is either **computational** (deterministic: lint, types, tests, structural
analysis) or **inferential** (LLM-based). GDSS leans on computational controls
first.

## Map of the harness

### Guides (feedforward)
- `AGENTS.md` - master operating manual: mission, commands, lifecycle, golden
  rules, TDD-first definition of done, and the two-brain (backend + frontend)
  map.
- Backend guides: `.cursor/rules/*.mdc` (00-60) - always-on context: GDSS
  mission, architecture invariants, math/domain glossary, python conventions,
  DSA optimization (`35-dsa-optimization.mdc`), verification/TDD, harness
  discipline, telemetry privacy.
- Frontend guides (the **visual brain**): `.cursor/rules/frontend/*.mdc`
  (01-20, `globs: web/**`) - design language, layout, motion, animation,
  state transitions, visual hierarchy, color, typography, composition,
  glassmorphism, data visualization, dashboard, loading/empty/error states,
  mobile, accessibility, performance, threejs, framer-motion.
- `.cursor/skills/*` - on-demand workflows:
  - Backend: `tdd`, `dsa-optimize`, `add-semantic-operator`,
    `implement-gdss-phase`, `verify-changes`, `audit-harness`.
  - Frontend: `motion-design`, `animation-system`, `component-composition`,
    `dashboard-design`, `ux-patterns`, `interaction-design`,
    `data-visualization`, `glass-ui`, `canvas-effects`, `webgl`,
    `framer-motion`, `gsap`, `svg-animation`, `build-frontend-component`,
    `verify-frontend`.

### Sensors (feedback)
- `.cursor/hooks.json` + `.cursor/hooks/*` - agent-lifecycle sensors:
  - `block-dangerous-git.sh` (`beforeShellExecution`) - blocks destructive git.
  - `run-fast-sensors.sh` (`afterFileEdit`) - backend syntax/lint/two-brain
    check on each `.py` edit (keep quality left).
  - `run-fast-frontend-sensors.sh` (`afterFileEdit`) - frontend token-fitness
    + eslint on each `web/**/*.{tsx,ts,css}` edit.
  - `audit-log.sh` (`afterShellExecution`) - observability to
    `harness/state/audit.log`.
- Backend gate `harness/verify.sh` - the externalized backend definition of
  done. A **three-layer validation hierarchy**, each layer gating the next:
  1. **static**: `sensors/lint.sh` (ruff) + `sensors/typecheck.sh` (mypy) +
     `sensors/architecture_fitness.py` + `sensors/dsa_fitness.py`
  2. **runtime**: `sensors/run_tests.sh` (pytest)
  3. **end-to-end**: `sensors/cli_smoke.sh` (gdss CLI over a fixture repo)
- Frontend gate `harness/verify-frontend.sh` - the externalized frontend
  definition of done. A **three frontend layers**, each gating the next and
  degrading gracefully when the JS toolchain is absent:
  1. **F1 static**: `sensors/frontend/lint.sh` (eslint + jsx-a11y) +
     `sensors/frontend/typecheck.sh` (tsc) + `sensors/frontend/token_fitness.py`
  2. **F2 component**: `sensors/frontend/component_tests.sh` (vitest + jest-axe)
  3. **F3 end-to-end**: `sensors/frontend/e2e.sh` (Playwright axe-core a11y +
     CLS ~ 0, and `size-limit` bundle budget)
  `verify.sh` invokes `verify-frontend.sh` automatically when `web/` exists.
- `harness/sensors/architecture_fitness.py` - custom structural sensor (ArchUnit
  style) enforcing layer direction + two-brain purity. Read-only over `gdss/`.
- `harness/sensors/dsa_fitness.py` - custom static sensor checking for O(N^2) loops,
  linear membership tests, graph copy operations, and repeated calls, with a
  baseline exception list (`dsa_baseline.json`).
- `harness/sensors/frontend/token_fitness.py` - custom frontend sensor enforcing
  the single-source-of-truth token rule (no raw hex/ms/`linear` outside token
  files; reduced-motion present on interactive motion components).
- `ruff.toml`, `mypy.ini` - standalone backend tool config (pyproject.toml
  untouched). `web/.eslintrc.cjs`, `web/tsconfig.json`, `web/.size-limit.json` -
  standalone frontend tool config.
- Frontend tokens (single source of truth the sensors lint against):
  `web/lib/tokens.ts` (spacing/color/type) and `web/lib/motion.ts`
  (duration/easing/spring/8-state machine/animation levels 0-10).

### State + Lifecycle
- `harness/init.sh` - idempotent bootstrap + health check; run at session start.
- `harness/state/feature_list.json` - machine-readable scope (one feature at a
  time) for **both** backend phases and `frontend-*` product phases, plus
  `harness_findings` (defects the harness discovered).
- `docs/FRONTEND_ROADMAP.md` - human-readable frontend product phases and how
  they complement backend layers (API-first: hard-gates -> local API -> shell
  -> status/graph/drift/similarity -> tensor/AI/validation/3D).
- `harness/state/progress.md` - per-session log with evidence.
- `harness/state/session-handoff.md` - clean restart path for the next session.
- `harness/state/audit.log` - executed-command trail (created by the hook).

### Frontend product phases (shared queue)

Ids in `feature_list.json`: `frontend-harness` (done) -> `frontend-hard-gates`
-> `frontend-local-api` -> `frontend-app-shell` -> status / semantic-graph /
drift-alerts / similarity (parallelizable after shell) -> conflict-tensor /
ai-suggestions / validation-ui / manifold-3d (wait on backend deps). Full map:
`docs/FRONTEND_ROADMAP.md`.

## Regulation categories (what the harness governs)

- **Maintainability**: ruff, mypy, fast-edit sensor (backend); eslint, tsc,
  token_fitness, fast-frontend-edit sensor (frontend).
- **Architecture fitness**: `architecture_fitness.py` (layers + two brains).
- **Behaviour**: TDD (the `tdd` skill + rule), pytest runtime layer, and the
  end-to-end CLI layer that catches cross-component boundary defects.
- **Visual quality (frontend)**: token_fitness (single source of truth),
  jsx-a11y + jest-axe + axe-core (accessibility), CLS ~ 0 (no layout shift),
  size-limit (bundle budget), and the frontend rules/skills that teach motion,
  hierarchy, state transitions, and the GDSS manifold visual language.

## Usage

```bash
bash harness/init.sh              # start of session: bootstrap + health (backend)
bash harness/verify.sh            # the gate: backend layers + frontend (if web/ exists)
bash harness/verify-frontend.sh   # the frontend gate alone (F1 -> F2 -> F3)
cd web && pnpm install            # one-time: install the frontend toolchain
```

## Growing the harness: the ratchet principle

The harness only tightens, never loosens. When a mistake recurs:

- The agent didn't know a rule -> add a **guide** (a rule or an `AGENTS.md` line).
- The agent knew but did it anyway -> add a **sensor** (a hook, a lint rule, or a
  check in `architecture_fitness.py`), wired into `verify.sh`.

Every guide line and every sensor should trace to a real failure - no
aspirational rules. Use the `audit-harness` skill to do this. Example: session 0
already recorded `finding-rename-downstream-crash` (caught by the end-to-end
layer) in `feature_list.json`.
