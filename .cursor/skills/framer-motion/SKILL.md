---
name: framer-motion
description: Use Framer Motion with GDSS motion tokens - variants, AnimatePresence, layoutId, whileHover/whileTap/whileFocus, drag/inertia, and useReducedMotion. Use when implementing animations in web/ with Framer Motion.
---

# Framer Motion (GDSS)

Framer Motion is the primary animation library. Tokens in `web/lib/motion.ts`.

## Conversions

- Durations: Framer uses **seconds** -> `duration.primary / 1000`.
- Easings: import `easing` arrays (cubic-bezier tuples); never `"linear"`.
- Springs: use `spring.snap/gentle/bouncy` presets.

## Core patterns

- **Variants** + `staggerChildren` for anatomy/list reveals (`revealStagger`).
- **`AnimatePresence`** around removable items for exit animations.
- **`layoutId`** for shared-layout morphs (card -> detail).
- **`whileHover` / `whileTap` / `whileFocus`** for micro-interactions (Levels 1-3).
- **`drag` + `dragConstraints` + `inertia`** for physics.

## State machine -> variants

```tsx
const variants = {
  idle: { /* resting */ },
  hover: { /* whileHover */ },
  pressed: { /* whileTap */ },
  loading: { /* progress affordance */ },
  success: { /* overshoot, then idle */ },
  // focused -> CSS :focus-visible; disabled -> aria-disabled
};
```

## Rules

- Animate only `transform`/`opacity` (see `18-performance`).
- `useReducedMotion()` -> disable non-essential motion (see `17-accessibility`).
- Tree-shakeable imports; don't pull the whole library.

## Reference

`web/components/ui/button.tsx` and `metric-card.tsx` show canonical usage.
See `.cursor/rules/frontend/20-framer-motion`.
