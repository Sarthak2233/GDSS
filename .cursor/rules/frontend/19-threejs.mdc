---
description: Three.js / React Three Fiber for GDSS frontend
globs: web/**
alwaysApply: false
---

# Three.js + React Three Fiber

Use 3D to render the GDSS **semantic manifold** as a geometric space where the
math is literally visible: nodes as points on a manifold, edges as geodesics,
trajectories as animated curves, merges as convergence.

## When to use 3D

- The manifold / geometric view (the signature GDSS visualization).
- Spatial drift and trajectory animations that are genuinely 3D.

Do NOT use 3D for flat dashboards, tables, or simple metrics - use React Flow /
D3 instead (cheaper, more accessible).

## Rules

- Lazy-load R3F so it never bloats the initial bundle (see `18-performance`).
- Provide a 2D fallback (React Flow) for low-power devices and
  `prefers-reduced-motion` (3D ambient motion is vestibular-sensitive).
- Animate via `useFrame` on `transform`/material opacity; avoid per-frame
  allocations (GC stalls).
- Cap draw calls and instancing for large node counts; use `InstancedMesh`.
- Respect device pixel ratio (`dpr={[1, 2]}`) to avoid retina overdraw.

## Manifold mapping

| Concept    | 3D representation                          |
| ---------- | ------------------------------------------ |
| Manifold   | curved surface / point cloud               |
| Node       | instanced point, breathes (scale pulse)    |
| Edge       | line/geodesic, pulses along flow           |
| Conflict   | glowing danger-colored node/edge           |
| Drift      | trajectory curve moving away from attractor |
| Merge      | two trajectories converging to a point     |

## WebGL shaders

For GPU effects (e.g. manifold field visualization), write GLSL shaders in
`web/shaders/`. Keep them small and well-typed; provide a fallback material.
See `.cursor/skills/webgl`.
