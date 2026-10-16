---
name: dashboard-design
description: Design GDSS dashboards that surface repository geometry - attractor, trajectory, drift, conflicts, impact. Use when building dashboard views, metric cards, or the manifold/graph visualization in web/.
---

# Dashboard Design (GDSS)

GDSS dashboards are instruments, not marketing pages. They surface repository
geometry: attractor, trajectory, drift, conflicts, impact.

## Numbers: never a bare number

Always show **Trend + Context + Comparison + Animation**.

Instead of `125`, display:

```
↑ 125   +14%   Today   [Animated Counter]   [Sparkline]   [Pulse]
```

Reference: `web/components/ui/metric-card.tsx`.

## Layout

- One hero metric/graph per view (the semantic graph / manifold view gets the
  most space).
- Secondary metrics in a card grid below.
- Spacing communicates hierarchy (Hero -> Section -> Card -> Widget -> Content
  -> Metadata).

## Live data

- Skeleton first (zero CLS), cross-fade to data, never jump-cut.
- Animate counters previous -> new over `duration.slow`.
- Sparkline = trend, pulse = liveness; keep ambient below distraction.

## State

Every widget handles loading/empty/error independently. A failing widget
must not take down the dashboard (error boundary per widget). See
`.cursor/rules/frontend/12-dashboard`.
