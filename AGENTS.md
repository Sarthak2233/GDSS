# AGENTS.md - GDSS Operating Manual

This is the master guide for any AI coding agent working in this repository. It is the
feedforward layer of the GDSS harness (see `harness/README.md` for the full harness map).

Read this first. Then run the startup lifecycle. Do not skip the verification gate.

---


## What GDSS is

GDSS (Gate Distributive Semantic Synopsis) is a **Semantic Branch Intelligence and Merge Assistance Platform** (PR Collision Radar
& Convergence Assistant), built as a semantic intelligence layer above Git:

1. **Repository Intelligence (Deterministic Core):** Tracks branches, commits, AST symbols,
   and dependency call/import graphs to identify affected symbols and contractual changes.
2. **PR Collision Radar:** Computes pairwise branch interaction ($\Omega_{ij}$), detecting
   non-commutative operations and semantic overlap across concurrent pull requests before merge.
3. **AI Convergence Assistant:** Pinpoints collision topologies, explains risks in plain
   English, proposes minimal conflict-free patches, and recommends optimal merge orders.
4. **Sandboxed Validation:** Tests candidate patches in ephemeral Git worktrees (syntax,
   types, targeted tests) before human review. Never auto-merges; humans decide what lands.

Canonical specification: [`PRODUCT_SPEC.md`](PRODUCT_SPEC.md).  
Implementation gap: [`docs/IMPLEMENTATION_GAP.md`](docs/IMPLEMENTATION_GAP.md).  
Product intent: [`docs/PRODUCT_INTENT.md`](docs/PRODUCT_INTENT.md).

### Deployment & Inference Architecture (Zero Token Bleed)
1. **MCP Tool Server (IDE First):** Exposes deterministic analysis tools to Cursor, Claude Code,
   and Copilot. The developer's AI client powers the chat conversation using their own account.
   GDSS incurs $0 token cost.
2. **GitHub Actions (PR Automation):** Audits incoming PRs, posts collision radar reports, and
   uses repo-entitled Copilot CLI/Models or user API keys.
3. **Local CLI Agent:** Runs completely offline on developer laptops with optional Ollama/vLLM.
4. **Hosted / Enterprise:** Future managed service for centralized organization policies.

## What GDSS is NOT

- Not a Git wrapper, chatbot, or general autocomplete tool.
- Not a perfect-code factory — it does not guarantee bug-free merges.
- Not a "universal merge oracle" — program equivalence and halting are undecidable; GDSS builds
  probabilistic approximations for common refactors and API shifts.
- Never auto-merges without human approval. Proposes and validates; humans decide.
- Theoretical differential geometry (Riemannian metric $G$, parallel transport $P$, rank-$N$
  octopus tensors on $M^N$) belongs to **Phase R (Research Track)**; it does not block product
  delivery.

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
