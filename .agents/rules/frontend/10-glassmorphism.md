---
description: Glassmorphism for GDSS frontend
globs: web/**
alwaysApply: false
---

# Glassmorphism

Use glass (frosted translucent surfaces) sparingly to create depth and separate
floating layers from the base surface. It reinforces the "manifold above a flat
codebase" metaphor.

## Tokens

- `surfaceGlass`: `rgba(23, 27, 36, 0.6)` (from `colors` in tokens)
- Combine with `backdrop-blur` and a 1px `border` hairline.

## Rules

- Glass is for **floating layers** (modals, popovers, tooltips, command palettes,
  overlays on the graph). Do not glass-ify the whole app - it kills performance
  and hierarchy.
- Always pair glass with a readable border and sufficient text contrast.
- Provide a non-blur fallback for browsers without `backdrop-filter` and for
  `prefers-reduced-motion` (blur can be vestibular-sensitive).
- One shadow layer under glass to ground it in space.

## Performance

`backdrop-filter: blur()` is expensive. Limit to a few simultaneous glass
surfaces. See `18-performance`. The bundle/CLS gates will catch regressions.
