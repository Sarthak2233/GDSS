# AGENTS.md - GDSS Operating Manual

This is the master guide for any AI coding agent working in this repository. It is the
feedforward layer of the GDSS harness (see `harness/README.md` for the full harness map).

Read this first. Then run the startup lifecycle. Do not skip the verification gate.

---


## What GDSS is

GDSS (Geometric Distributed Software Synchronizer) is a **semantic intelligence layer above
Git**. It treats collaborative software development as a continuous geometric-semantic
dynamical system:

> ⚠️⚠️⚠️⚠️⚠️ **Important Warning**
>
>The number of branch defines the construction of the mathematics around this project.
>You can take a reference from here about some concepts 
https://ocw.mit.edu/courses/18-994-seminar-in-geometry-fall-2004/f8e7b8f1462fe0b3abfd22f7b79c16dd_chapter16.pdf


- A repository state is a point on a semantic manifold `M`.
- A branch is a trajectory `gamma_i(t)` on `M`.
- A commit is a tangent vector / transformation `dC`.
- A merge conflict is non-commutativity of transformations: `[T_i, T_j] != 0`.
- Branch interaction is the conflict tensor `Omega_{ij}`.
- The `dev`/reference branch is the attractor trajectory all branches are measured against.

The product goal: detect semantic branch drift, identify affected symbols, and predict
likely conflicts and convergence **before** merge. See the source vision in
`FROM WHERE IT ALL STARTED..txt` and the phased plan in
`.cursor/plans/gdss_complete_roadmap_e8cc388d.plan.md`.

GDSS is designed across three deployment tiers:
1. **Local CLI Agent:** The core parser, extractor, and drift monitor. Runs completely offline on developer machines.
2. **Hybrid Cloud SaaS:** Aggregates metadata for org-wide analytics, dashboards, and conflict tensor alerts.
3. **Self-Hosted Enterprise:** On-premise turnkey appliance for absolute data sovereignty (SOC2/GDPR ready).

## What GDSS is NOT

- Not a Git wrapper, chatbot, or autocomplete tool.
- Not a "perfect universal merge oracle" - semantic equivalence and halting are undecidable.
  GDSS builds **probabilistic approximations** for the common cases (renames, refactors, API
  changes) and is honest about the limits.

---

## Build, test, verify commands

```bash
# Bootstrap the environment (idempotent: venv + editable install + health checks)
bash harness/init.sh

# Run the full verification gate (the definition of done)
bash harness/verify.sh

# Individual sensors
bash harness/sensors/lint.sh          # ruff (Layer 1)
bash harness/sensors/typecheck.sh     # mypy (Layer 1)
python harness/sensors/architecture_fitness.py   # layer + two-brain boundaries (Layer 1)
bash harness/sensors/run_tests.sh     # pytest (Layer 2)
bash harness/sensors/cli_smoke.sh     # gdss CLI end-to-end (Layer 3)

# The CLI itself
gdss --help
gdss status
gdss log -n 5

# Frontend (web/) - the visual brain
cd web && pnpm install        # one-time: install the frontend toolchain
cd web && pnpm dev            # local dev server
cd web && pnpm lint           # eslint + jsx-a11y (frontend Layer F1)
cd web && pnpm typecheck      # tsc --noEmit (frontend Layer F1)
cd web && pnpm test           # vitest + jest-axe (frontend Layer F2)
cd web && pnpm size           # size-limit bundle budget (frontend Layer F3)
bash harness/verify-frontend.sh   # the full frontend gate (F1 -> F2 -> F3)
```

---

## Two brains

GDSS has two harnesses, each with its own feedforward guides and feedback sensors:

- **Backend brain** (correctness): `gdss/` Python. Answers *"How should an AI
  write correct code?"* Guides: `.cursor/rules/*.mdc` (00-60). Sensors:
  `harness/verify.sh` (ruff, mypy, architecture fitness, pytest, CLI smoke).
- **Frontend brain** (visual quality): `web/` Next.js. Answers *"How should an
  AI create an interface that feels polished, intuitive, and alive?"* Guides:
  `.cursor/rules/frontend/*.mdc` (01-20) + `.cursor/skills/*` (motion,
  animation, composition, dashboard, a11y, etc.). Sensors:
  `harness/verify-frontend.sh` (eslint+jsx-a11y, tsc, token_fitness, vitest+
  jest-axe, Playwright a11y/CLS, size-limit).

`harness/verify.sh` runs the backend layers, then the frontend gate **only when
`web/` exists** (no-op otherwise), so there is still one green definition of
done. Frontend sensors degrade gracefully (skip with WHAT/WHY/FIX) when the JS
toolchain is absent, so the gate stays runnable on a Python-only machine.

---

## Startup lifecycle (do this every session)

1. Read this file (`AGENTS.md`).
2. Run `bash harness/init.sh` and confirm it reports healthy.
3. Read `harness/state/progress.md` (what happened last session).
4. Read `harness/state/feature_list.json` (shared queue: backend **and**
   `frontend-*` product phases). For frontend vision/complementarity, also read
   `docs/FRONTEND_ROADMAP.md`.
5. Check recent history (`git log` if this is a git repo) for context.
6. Select exactly **one** unfinished feature whose `deps` are all `done`. Do not
   start three things at once. Backend or frontend — same queue.
7. Implement it test-first (backend: TDD skill below; frontend product work:
   `build-frontend-component` + `verify-frontend` skills).
8. Run `bash harness/verify.sh`. It must be green. Frontend product features
   (`frontend-*`) also need `bash harness/verify-frontend.sh` green.
9. Update `harness/state/progress.md` and `harness/state/feature_list.json`.
10. Write `harness/state/session-handoff.md` so the next session can resume cleanly.

---

## TDD-first definition of done

"Done" is **not** "the code is written". Agents are systematically overconfident, so
completion is judged by externalized evidence, not by your confidence.

A change is done only when the **three-layer validation hierarchy** is green:

- **Layer 1 - Static**: `ruff`, `mypy`, and the architecture fitness sensor pass.
- **Layer 2 - Runtime**: `pytest` passes.
- **Layer 3 - End-to-end**: the `gdss` CLI runs over a fixture repo without error.

Each layer gates the next. `bash harness/verify.sh` runs all three. If it exits non-zero,
the work is not done.

### Frontend definition of done (web/)

Frontend work is done only when the **three frontend layers** are green (or skip
cleanly when the JS toolchain is absent):

- **Layer F1 - Static**: `eslint` (+ `jsx-a11y`), `tsc --noEmit`, and the
  `token_fitness` sensor (no raw hex/ms/`linear` outside token files; every
  interactive motion component ships a `prefers-reduced-motion` branch).
- **Layer F2 - Component**: `vitest` + `jest-axe` behavior and accessibility tests pass.
- **Layer F3 - End-to-end**: optional Playwright `axe-core` (keyboard nav + a11y)
  with CLS ~ 0, and a `size-limit` bundle budget.

Run all three with `bash harness/verify-frontend.sh` (also invoked by
`harness/verify.sh` when `web/` exists). See the `build-frontend-component` and
`verify-frontend` skills.

### How to write code here

- **Write the failing test first.** Red -> Green -> Refactor.
- Work in **vertical slices**: one test -> one minimal implementation -> repeat. Never write
  all tests first then all code.
- **Never refactor while red.** Get to green first.
- **No premature optimization.** Verify core behavior before touching performance or style.
- Tests verify **behavior through public interfaces**, not implementation details.
- **Mock only at true system boundaries.** Prefer real `tree-sitter` and `GitPython`; do not
  mock GDSS's own modules.

See the `tdd` skill in `.cursor/skills/tdd/` for the full loop.

---

## Golden rules

- **No edits to existing source.** Do not modify files under `gdss/`, `tests/`, or
  `pyproject.toml` unless the user explicitly asks. The harness is additive.
- **Two-brain purity.** The deterministic brain (`gdss/core`, `gdss/graph`, `gdss/watcher`)
  must never import the probabilistic brain (`gdss/embeddings`, `gdss/ai`). The probabilistic
  brain never acts without deterministic validation.
- **Respect layer direction.** Higher layers depend on lower layers, never the reverse. The
  architecture fitness sensor enforces this.
- **Never auto-merge.** GDSS predicts and suggests; it does not silently resolve conflicts.
- **Telemetry & Privacy are absolute.** GDSS collects *no source code* and *no PII*. Telemetry features must only process anonymized metadata and must fully support an opt-out flag.
- **Errors are for agents.** When you add a sensor, write failure messages as WHAT / WHY /
  FIX so the next agent can self-correct.
- **Apply the ratchet.** Whenever a mistake recurs, tighten the harness (add a guide or a
  sensor) so it cannot recur. See the `audit-harness` skill.
- **DSA-first coding.** Choose data structures deliberately. Every public function
  should have justifiable time/space complexity. See `.cursor/rules/35-dsa-optimization.mdc`
  for the selection matrix and `.cursor/skills/dsa-optimize/` for the workflow.

---

## Where things live

- Guides (feedforward): this file + `.cursor/rules/*.mdc` + `.cursor/skills/*`
  - Backend: `.cursor/rules/00-60-*.mdc`; skills: `tdd`, `add-semantic-operator`, `implement-gdss-phase`, `verify-changes`, `audit-harness`, `dsa-optimize`.
  - Frontend: `.cursor/rules/frontend/01-20-*.mdc` (globs `web/**`); skills: `motion-design`, `animation-system`, `component-composition`, `dashboard-design`, `ux-patterns`, `interaction-design`, `data-visualization`, `glass-ui`, `canvas-effects`, `webgl`, `framer-motion`, `gsap`, `svg-animation`, `build-frontend-component`, `verify-frontend`.
- Sensors (feedback): `.cursor/hooks/*` + `harness/verify.sh` + `harness/sensors/*` (backend) + `harness/verify-frontend.sh` + `harness/sensors/frontend/*` (frontend)
- Tokens (frontend single source of truth): `web/lib/tokens.ts` (spacing/color/type), `web/lib/motion.ts` (duration/easing/spring/8-state machine/animation levels)
- Product scope: `harness/state/feature_list.json` (backend + `frontend-*`); roadmap narrative: `docs/FRONTEND_ROADMAP.md`
- State + lifecycle: `harness/state/*` + `harness/init.sh`
- Harness map and rationale: `harness/README.md`
