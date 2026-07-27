---
description: Dashboard design for GDSS frontend
globs: web/**
alwaysApply: false
---

# Dashboard Design

GDSS surfaces repository geometry: attractor, trajectory, drift, conflicts,
impact. The dashboard is an instrument, not a marketing page.

## Numbers: Trend + Context + Comparison + Animation

Never show a bare number. Always:

```
Trend + Context + Comparison + Animation
```

Instead of `125`, display:

```
↑ 125   +14%   Today   [Animated Counter]   [Sparkline]   [Pulse]
```

Reference: `web/components/ui/metric-card.tsx`.

## Layout

- One hero metric or graph per view as the focal point.
- Secondary metrics in a card grid below.
- Reserve the largest space for the semantic graph / manifold view.
- Spacing communicates hierarchy (see `06-visual-hierarchy`).

## Anatomy

```
Hero -> Section -> Card -> Widget -> Content -> Metadata
```

Each card: Container -> Header -> Body -> Actions -> Footer, revealed staggered.

## Live data

- Skeletons first (see `13-loading-states`), cross-fade to data, never jump-cut.
- Animate counters from previous -> new value over `duration.slow`.
- Sparklines show trend; pulses show liveness; never block perception with
  busy ambient motion.

## State

Every dashboard widget handles loading/empty/error (see `13`/`14`/`15`). A
widget that errors must not take down the whole dashboard.
