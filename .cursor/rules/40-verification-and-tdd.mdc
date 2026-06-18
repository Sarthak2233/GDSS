---
description: Mandatory TDD and the externalized definition of done
alwaysApply: true
---

# Verification and TDD

## TDD is mandatory

- Write the **failing test first**. Red -> Green -> Refactor.
- Work in **vertical slices**: one test -> one minimal implementation -> repeat. Never write
  all tests first, then all code.
- **Never refactor while red.** Get to green first, then refactor.
- **No premature optimization.** Verify core behavior before touching performance or style.
- Tests assert **behavior through public interfaces**, not implementation details, so they
  survive refactors.
- **Mock only at true system boundaries.** Prefer real `tree-sitter` and `GitPython`; do not
  mock GDSS's own modules.

See the `tdd` skill (`.cursor/skills/tdd/`) for the full loop and good/bad test examples.

## Definition of done (externalized)

Agents are systematically overconfident, so "done" is decided by evidence, not confidence.
A change is done only when the **three-layer validation hierarchy** is green, each layer
gating the next:

1. **Static**: `ruff`, `mypy`, `architecture_fitness.py`.
2. **Runtime**: `pytest`.
3. **End-to-end**: the `gdss` CLI runs over a fixture repo.

Run all three with `bash harness/verify.sh`. If it exits non-zero, the work is not done.
"The code is written" is never sufficient.

## Agent-oriented errors

When you add or change a sensor, format failures as WHAT happened / WHY it is wrong / FIX to
apply, so the next agent can self-correct without a human.
