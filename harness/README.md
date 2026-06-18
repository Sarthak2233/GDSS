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
  rules, TDD-first definition of done.
- `.cursor/rules/*.mdc` - always-on context: GDSS mission, architecture
  invariants, math/domain glossary, python conventions, DSA optimization
  (`35-dsa-optimization.mdc`), verification/TDD, harness discipline.
- `.cursor/skills/*` - on-demand workflows: `tdd`, `dsa-optimize`,
  `add-semantic-operator`, `implement-gdss-phase`, `verify-changes`,
  `audit-harness`.

### Sensors (feedback)
- `.cursor/hooks.json` + `.cursor/hooks/*` - agent-lifecycle sensors:
  - `block-dangerous-git.sh` (`beforeShellExecution`) - blocks destructive git.
  - `run-fast-sensors.sh` (`afterFileEdit`) - syntax/lint/two-brain check on
    each edit (keep quality left).
  - `audit-log.sh` (`afterShellExecution`) - observability to
    `harness/state/audit.log`.
- `harness/verify.sh` - the externalized definition of done. A **three-layer
  validation hierarchy**, each layer gating the next:
  1. **static**: `sensors/lint.sh` (ruff) + `sensors/typecheck.sh` (mypy) +
     `sensors/architecture_fitness.py` + `sensors/dsa_fitness.py`
  2. **runtime**: `sensors/run_tests.sh` (pytest)
  3. **end-to-end**: `sensors/cli_smoke.sh` (gdss CLI over a fixture repo)
- `harness/sensors/architecture_fitness.py` - custom structural sensor (ArchUnit
  style) enforcing layer direction + two-brain purity. Read-only over `gdss/`.
- `harness/sensors/dsa_fitness.py` - custom static sensor checking for O(N^2) loops,
  linear membership tests, graph copy operations, and repeated calls, with a
  baseline exception list (`dsa_baseline.json`).
- `ruff.toml`, `mypy.ini` - standalone tool config (pyproject.toml untouched).

### State + Lifecycle
- `harness/init.sh` - idempotent bootstrap + health check; run at session start.
- `harness/state/feature_list.json` - machine-readable scope (one feature at a
  time) + `harness_findings` (defects the harness discovered).
- `harness/state/progress.md` - per-session log with evidence.
- `harness/state/session-handoff.md` - clean restart path for the next session.
- `harness/state/audit.log` - executed-command trail (created by the hook).

## Regulation categories (what the harness governs)

- **Maintainability**: ruff, mypy, fast-edit sensor.
- **Architecture fitness**: `architecture_fitness.py` (layers + two brains).
- **Behaviour**: TDD (the `tdd` skill + rule), pytest runtime layer, and the
  end-to-end CLI layer that catches cross-component boundary defects.

## Usage

```bash
bash harness/init.sh      # start of session: bootstrap + health
bash harness/verify.sh    # the gate: must be green to call work done
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
