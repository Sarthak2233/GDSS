---
name: animation-system
description: Build a reusable animation system with Framer Motion variants, staggered reveals, AnimatePresence exits, shared-layout layoutId, and spring physics. Use when creating shared animation variants, enter/exit systems, or physics-based interactions in web/.
---

# Animation System (GDSS)

A small, composable set of shared variants beats scattered one-off animations.
Centralize in `web/lib/motion.ts`; consume everywhere.

## Shared variants

`web/lib/motion.ts` exports `revealStagger` (container + item) for anatomy
reveals. Build feature variants on top of these, never redefining durations.

## Enter / exit

- Wrap removable items in `AnimatePresence` so exit animations run.
- Appear: opacity 0->1, y 8->0, `duration.primary`, `easeOut`.
- Disappear: opacity 1->0, y 0->-8, `duration.slow`, `easeIn`.

## Shared layout

`layoutId` morphs an element between positions (card -> detail). Keep the
shared `layoutId` stable across the two views.

## Physics

Use `spring.snap` (toggles), `spring.gentle` (drag release), `spring.bouncy`
(success). Pair with `drag` + `dragConstraints` + `inertia`.

## Rules

- Durations in seconds for Framer (`duration.x / 1000`).
- Never `"linear"`; import `easing` arrays.
- Animate only `transform`/`opacity`.
- `useReducedMotion()` -> disable non-essential motion.

## Levels

Every animation declares its level (see `motion-design` skill). The system
should make the *common* levels (1 hover, 4 appear, 6 state change) trivial and
the *rare* levels (9 background, 10 physics) explicit.
