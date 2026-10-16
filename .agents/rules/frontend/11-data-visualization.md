---
description: Data visualization for GDSS frontend
globs: web/**
alwaysApply: false
---

# Data Visualization

GDSS is mathematical; the UI must make the underlying concepts *visible*, not
just described. Prefer animated graphs over tables.

## GDSS manifold visualizations

| Concept    | Visualization                          |
| ---------- | -------------------------------------- |
| Semantic graph | animated graph (React Flow / R3F)  |
| Nodes      | breathe (low-amplitude ambient, Level 9) |
| Edges      | pulse (data flowing along trajectory) |
| Conflicts  | glow (danger color, demands attention) |
| Drift      | moves (trajectory diverges from attractor) |
| Trajectory | animates (integral of tangent vectors) |
| Merge      | converges (geodesic path convergence)  |

## Tooling

- Node graphs: **React Flow** for 2D interactive graphs.
- 3D manifold: **Three.js + React Three Fiber** for the geometric manifold
  view (see `19-threejs`).
- Charts/sparklines: **D3.js** or **Visx** for precise, composable charts.
- Always animate `transform`/`opacity`, never `width/height` (see `18-performance`).

## Dashboard numbers (never a bare number)

Never show just a number. Always show:

```
Trend + Context + Comparison + Animation
```

Example - instead of `125`, display:

```
↑ 125   +14%   Today   [Animated Counter]   [Sparkline]   [Pulse]
```

See `12-dashboard` and `web/components/ui/metric-card.tsx`.

## Rules

- Encode meaning in motion/color, never decoration.
- Provide a static, readable fallback for `prefers-reduced-motion`.
- Label axes and units; a chart without context is noise.
