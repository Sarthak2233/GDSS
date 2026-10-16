---
name: svg-animation
description: Animate SVG in GDSS - path morphing, clipPath/mask reveals, stroke-dashoffset line drawing, and Lottie. Use when animating icons, illustrations, sparklines, or SVG-based manifold visuals in web/.
---

# SVG Animation (GDSS)

SVG is ideal for crisp, scalable, animatable graphics: icons, illustrations,
sparklines, and 2D manifold visuals.

## Techniques

- **Line drawing**: animate `stroke-dashoffset` from full length to 0 to "draw"
  edges/trajectories. Use `pathLength={1}` + `strokeDasharray="1"` in Framer.
- **Path morph**: animate `d` between shapes (same point count) with Framer
  Motion or GSAP MorphSVG.
- **clipPath / mask reveals**: animate clip/mask geometry for wipes and
  shape transitions.
- **Lottie**: pre-authored illustrations via `lottie-react`, paused on
  `prefers-reduced-motion`.

## Rules

- SVG motion is cheap (no DOM layout) but still respect `prefers-reduced-motion`.
- Animate presentation attributes (`stroke-dashoffset`, `opacity`, `transform`)
  not layout.
- For sparklines (see `metric-card.tsx`): draw-in over `duration.slow` with
  `easeOut`; pulse the latest point.
- Keep `viewBox` stable to avoid CLS; reserve space.

## Manifold 2D

Use SVG for a lightweight 2D manifold/graph fallback when 3D (R3F) is not
loaded (see `webgl` skill). Edges pulse via `stroke-dashoffset`; nodes breathe
via `transform: scale`.

See `.cursor/rules/frontend/04-animation` and `11-data-visualization`.
