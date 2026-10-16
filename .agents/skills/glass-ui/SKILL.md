---
name: glass-ui
description: Apply glassmorphism sparingly for floating layers in GDSS - modals, popovers, tooltips, overlays on the graph. Use when building floating/translucent surfaces in web/.
---

# Glass UI (GDSS)

Use glass (frosted translucent surfaces) to separate floating layers from the
base surface - it reinforces the "manifold above a flat codebase" metaphor.

## Tokens

- `surfaceGlass`: `rgba(23, 27, 36, 0.6)` (from `colors` in tokens).
- Pair with `backdrop-blur` + a 1px `border` hairline + one grounding shadow.

## When to use

Floating layers only: modals, popovers, tooltips, command palettes, overlays
on the graph. **Do not glass-ify the whole app** - it kills performance and
hierarchy.

## Rules

- Always pair glass with a readable border and sufficient text contrast.
- Provide a non-blur fallback for browsers without `backdrop-filter` and for
  `prefers-reduced-motion` (blur can be vestibular-sensitive).
- One shadow layer under glass to ground it in space.
- Limit simultaneous glass surfaces (expensive). See `18-performance`.

See `.cursor/rules/frontend/10-glassmorphism`.
