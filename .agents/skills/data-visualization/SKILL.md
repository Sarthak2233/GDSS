---
name: data-visualization
description: Visualize GDSS mathematical concepts - semantic graph, manifold, drift, trajectory, conflicts, merge - with React Flow, D3/Visx, and animated encodings. Use when building graphs, charts, sparklines, or the manifold view in web/.
---

# Data Visualization (GDSS)

GDSS is mathematical; make the concepts *visible*, not just described. Prefer
animated graphs over tables.

## Manifold mapping

| Concept       | Visualization                              |
| ------------- | ------------------------------------------ |
| Semantic graph| animated graph (React Flow / R3F)           |
| Nodes         | breathe (low-amplitude ambient, Level 9)  |
| Edges         | pulse (data flowing along trajectory)     |
| Conflicts     | glow (danger, demands attention)          |
| Drift         | moves (trajectory diverges from attractor)|
| Trajectory    | animates (integral of tangent vectors)    |
| Merge         | converges (geodesic path convergence)      |

## Tooling

- **React Flow** - 2D interactive node graphs (dependencies, call graph).
- **D3.js / Visx** - precise, composable charts and sparklines.
- **Three.js + R3F** - the 3D manifold view (lazy-loaded; see `webgl` skill).

## Rules

- Encode meaning in motion/color, never decoration.
- Animate `transform`/`opacity` only; never `width/height`.
- Label axes and units; a chart without context is noise.
- Static, readable fallback for `prefers-reduced-motion`.
- Virtualize large graphs; cap simultaneous animated elements.

## Metric numbers

Never a bare number: Trend + Context + Comparison + Animation. See
`dashboard-design` skill and `web/components/ui/metric-card.tsx`.

See `.cursor/rules/frontend/11-data-visualization`.
