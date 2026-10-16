---
description: Empty states for GDSS frontend
globs: web/**
alwaysApply: false
---

# Empty States

An empty state is a first impression, not an error. It must teach the user what
is possible and how to get there.

## Required elements

- **Clear title** of what is empty (e.g. "No branches tracked yet").
- **Helpful explanation** of why and what to do next.
- **A primary action** to fill the void (e.g. "Analyze a repository").
- An optional illustration (SVG/Lottie) that fits the visual language - never
  a generic stock graphic.

## Rules

- Never show a bare "No data" string.
- Empty is a *real* state, distinct from loading and error.
- Use the visual hierarchy (see `06`): title > explanation > action.
- Keep motion minimal (Level 4 appear), no ambient loops on empty states.

## GDSS examples

- No repository analyzed -> "Analyze a repository" CTA.
- No conflicts -> positive empty state ("Trajectories commute - no conflicts").
- No drift -> "On the attractor" with a calm trajectory graphic.
