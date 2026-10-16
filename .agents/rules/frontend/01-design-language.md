---
description: GDSS frontend design language - the visual brain's foundation
globs: web/**
alwaysApply: false
---

# Design Language

GDSS is a geometric-semantic system. The UI must *look* mathematical, not like a
generic dashboard. The visual language reinforces the README's framing of code
as a semantic manifold.

## Core principles

- **Movement before color before text.** Motion guides attention; it is not
  decoration. See `03-motion` and `04-animation`.
- **Spacing communicates hierarchy before color.** Use the 4px spacing scale in
  `web/lib/tokens.ts`; never invent arbitrary spacing.
- **State is explicit.** Every interactive element reasons about the 8-state
  machine (see `05-state-transitions`).
- **Tokens are the single source of truth.** No raw hex/px/ms outside
  `web/lib/tokens.ts` and `web/lib/motion.ts`. Enforced by
  `harness/sensors/frontend/token_fitness`.

## The GDSS visual metaphor

| Concept        | Visual treatment                         |
| -------------- | ---------------------------------------- |
| Semantic graph | animated graph, not a table             |
| Nodes          | breathe (low-amplitude ambient)         |
| Edges          | pulse (data flowing along trajectory)   |
| Conflicts      | glow (non-commutativity = attention)    |
| Drift          | moves (trajectory diverges from attractor) |
| Trajectory     | animates (integral of tangent vectors)  |
| Merge          | converges (geodesic path convergence)    |

## Tone

Calm, precise, instrument-like. This is a tool for reasoning about software
geometry, not a marketing site. Prefer dark, deep surfaces with restrained
accents. Reserve saturated color for semantic meaning (conflict = danger,
trajectory = success, drift = warning).
