---
description: Animation implementation patterns for GDSS frontend
globs: web/**
alwaysApply: false
---

# Animation

Implementation patterns for the motion principles in `03-motion`. Tokens:
`web/lib/motion.ts`.

## Micro-interactions

Button: hover -> lift -> shadow -> scale -> cursor -> press -> release -> ripple -> success -> disabled
Toggle: slide -> snap -> glow -> color -> icon morph
Card:   hover -> elevation -> parallax -> gradient -> blur -> shadow

Use `duration.tiny` for the snap, `duration.primary` for the lift. Use
`easing.overshoot` only for delightful confirmations (success), never for
routine hovers.

## Component anatomy reveal (staggered)

Reveal in order: Container -> Header -> Body -> Actions -> Footer. Use the
shared `revealStagger` variants in `web/lib/motion.ts`.

## Advanced interactions

- **Shared layout**: Framer Motion `layoutId` to morph an element between
  positions (e.g. a card expanding to a detail view).
- **Animated lists**: `staggerChildren` + `AnimatePresence` for enter/exit.
- **Morphing**: SVG `clipPath` / `mask` + layout animations for shape changes.
- **Physics**: `spring` presets (`spring.snap`, `spring.gentle`,
  `spring.bouncy`) with `drag`, `dragConstraints`, `inertia`.

## Appear / disappear

- Appear: opacity 0 -> 1, y 8 -> 0, `duration.primary`, `easeOut`.
- Disappear: opacity 1 -> 0, y 0 -> -8, `duration.slow`, `easeIn`.
- Always wrap removable items in `AnimatePresence` so exit animations run.

## Ambient (Level 9)

Keep amplitude low and period long (3-5s) so it stays below the distraction
threshold. Examples: `breathe`, `pulse-edge`, `glow-conflict` keyframes in
`tailwind.config.ts`.

## Performance

Animate only `transform` and `opacity` (GPU-composited). Avoid animating
`width/height/top/left/box-shadow` directly; use `transform` + a layered
shadow. See `18-performance`.
