---
description: Frontend performance for GDSS
globs: web/**
alwaysApply: false
---

# Performance

Performance is a feature and a harness gate (bundle budget via `size-limit`,
CLS via Playwright).

## Animation performance

- Animate only `transform` and `opacity` (GPU-composited).
- Never animate `width`, `height`, `top`, `left`, or `box-shadow` directly;
  use `transform` + a layered shadow element.
- Cap simultaneous animated elements; ambient motion stays low-amplitude/long-period.

## Layout stability

- Zero CLS: reserve space for async content with skeletons/fixed-aspect
  containers before data arrives (see `13-loading-states`).
- Set explicit `width`/`height` (or aspect-ratio) on images, canvases, and
  graph containers.

## Bundle budget

- `size-limit` budgets in `web/package.json` (`size-limit` key) / `web/.size-limit.json`. A route's first JS must stay
  within budget; code-split heavy views (Three.js, D3) so they load on demand.
- Prefer `framer-motion`'s tree-shakeable imports; lazy-load R3F/D3.

## Rendering

- Avoid layout thrash: batch DOM reads before writes.
- Virtualize long lists (e.g. large node graphs).
- Memoize expensive graph computations; derive with `useMemo`/Zustand selectors.

## Reduced data / low power

- Detect `navigator.connection.saveData` / `effectiveType` to skip heavy 3D
  and ambient motion on slow networks (see `16-mobile`).
