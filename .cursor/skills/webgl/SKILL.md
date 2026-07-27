---
name: webgl
description: Write WebGL shaders and React Three Fiber scenes for the GDSS manifold view - GLSL shaders, instancing, dpr caps, and reduced-motion fallbacks. Use when building GPU effects or the 3D manifold visualization in web/.
---

# WebGL (GDSS)

WebGL is for the signature GDSS **manifold view** and GPU field effects where
the math is literally visible. Keep it lazy-loaded and fallback-friendly.

## Rules

- Lazy-load R3F/Three.js so it never bloats the initial bundle (see
  `18-performance`).
- Provide a 2D fallback (React Flow) for low-power devices and
  `prefers-reduced-motion` (3D ambient motion is vestibular-sensitive).
- Cap `dpr={[1, 2]}` to avoid retina overdraw.
- Use `InstancedMesh` for many nodes; cap draw calls.
- Animate in `useFrame` on `transform`/material opacity; avoid per-frame
  allocations (GC stalls).
- Dispose geometries/materials on unmount to avoid leaks.

## Shaders

- Keep GLSL small and well-typed; store in `web/shaders/`.
- Provide a fallback material when the shader/extension is unavailable.
- Guard against context loss (`gl.getExtension('WEBGL_lose_context')`).

## Manifold mapping

| Concept    | 3D representation                          |
| ---------- | ------------------------------------------ |
| Manifold   | curved surface / point cloud               |
| Node       | instanced point, breathes (scale pulse)    |
| Edge       | line/geodesic, pulses along flow           |
| Conflict   | glowing danger-colored node/edge           |
| Drift      | trajectory curve moving away from attractor |
| Merge      | two trajectories converging to a point     |

See `.cursor/rules/frontend/19-threejs` and the `canvas-effects` skill.
