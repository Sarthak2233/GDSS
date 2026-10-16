---
name: canvas-effects
description: Build GPU-composited canvas effects (2D canvas and WebGL) for GDSS ambient/background visuals - particle fields, manifold shimmer, edge flow. Use when creating ambient background animations or canvas-based effects in web/.
---

# Canvas Effects (GDSS)

Canvas is for **ambient/background** visuals (Level 9) that would be too
expensive in DOM: particle fields, manifold shimmer, edge-flow trails.

## When to use

- Ambient background motion behind the manifold view.
- Many particles / many lines that would overwhelm DOM nodes.

Do NOT use canvas for interactive controls or accessible content - keep that
in DOM with semantic HTML.

## Rules

- Use `requestAnimationFrame`; pause when tab hidden (`visibilitychange`).
- Cap pixel ratio (`devicePixelRatio`, max 2) to avoid retina overdraw.
- Pause/reduce on `prefers-reduced-motion` and low-power (see `18-performance`).
- Animate via transforms/alpha in-shader or via cheap draw calls; avoid
  per-frame allocations (GC stalls).
- Keep amplitude low, period long (3-5s) - below the distraction threshold.

## 2D vs WebGL

- 2D canvas: simple particle counts, easy to reason about.
- WebGL (R3F / raw): thousands of instances - use `InstancedMesh`. See
  `webgl` skill.

See `.cursor/rules/frontend/11-data-visualization` and `18-performance`.
