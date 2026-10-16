---
name: implement-gdss-phase
description: Workflow to implement one GDSS roadmap feature using the harness session lifecycle. Use when picking up work on a roadmap phase, starting a new GDSS feature, or continuing multi-session implementation work.
---

# Implement a GDSS Phase / Feature

Advance the GDSS roadmap one feature at a time, governed by the harness lifecycle.

## Scope source

Features and statuses live in `harness/state/feature_list.json`, derived from
`.cursor/plans/gdss_complete_roadmap_e8cc388d.plan.md` (7 phases, 10 layers). Pick exactly
one feature whose dependencies are already `done`.

## Lifecycle

```
[ ] 1. INIT:   bash harness/init.sh  (must report healthy)
[ ] 2. ORIENT: read harness/state/progress.md and feature_list.json
[ ] 3. SELECT: choose ONE unfinished feature with satisfied deps; set it in_progress
[ ] 4. PLACE:  create files in the correct layer/dir (see architecture-invariants rule)
[ ] 5. BUILD:  implement test-first (use the tdd skill), vertical slices
[ ] 6. VERIFY: bash harness/verify.sh is green (static -> tests -> end-to-end)
[ ] 7. STATE:  update progress.md + feature_list.json (status, evidence, next step)
[ ] 8. HANDOFF: write session-handoff.md for the next session
```

## Placement guide (two-brain + layers)

- Deterministic brain: `gdss/core`, `gdss/graph`, `gdss/watcher`. Must not import
  `gdss/embeddings` or `gdss/ai`.
- Probabilistic brain: `gdss/embeddings`, `gdss/ai`. May depend downward; never acts without
  deterministic validation.
- Entrypoints: `gdss/cli`, `gdss/api` may depend on any layer.

## Rules

- One feature at a time. Do not half-finish several.
- Do not edit existing `gdss/`, `tests/`, or `pyproject.toml` to force-fit a feature unless
  the user asks; design around the invariants.
- Done = `harness/verify.sh` green + state updated. Not "code written".
