---
description: How to operate and grow the GDSS harness
alwaysApply: true
---

# Harness Discipline

This repo is governed by a harness (guides + sensors). Operate inside it.

## No-edit zones

Do not modify existing source unless the user explicitly asks:

- `gdss/**` (project source)
- `tests/**` (existing test baseline; you may ADD new tests)
- `pyproject.toml`

The harness is additive. New tool config lives in standalone files (`ruff.toml`, `mypy.ini`).

## Keep quality left

Run fast sensors (lint, type-check, affected tests) as early as possible - ideally as you
edit, not only at the end. Cheap checks first, expensive checks later.

## Update state every session

- `harness/state/progress.md` - what you did, with evidence (verify output).
- `harness/state/feature_list.json` - statuses and next step.
- `harness/state/session-handoff.md` - a clean restart path for the next session.

## The ratchet principle

The harness only tightens. Whenever a mistake happens more than once:

1. If the agent did not know a rule -> add a guide (rule or `AGENTS.md` line).
2. If the agent knew but violated it -> add a sensor (hook, lint rule, or check in
   `architecture_fitness.py`).

Every guide line and every sensor should trace to a real failure. No aspirational rules.
Use the `audit-harness` skill to do this systematically.

## One feature at a time

Select exactly one unfinished feature from `feature_list.json`. Do not half-finish several.
