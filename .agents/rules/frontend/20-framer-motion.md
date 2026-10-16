---
description: Framer Motion for GDSS frontend
globs: web/**
alwaysApply: false
---

# Framer Motion

Framer Motion is GDSS's primary animation library. Tokens in
`web/lib/motion.ts` (durations in seconds for Framer, easings as arrays,
springs as presets).

## Core patterns

- **Variants** with `staggerChildren` for list/anatomy reveals (use
  `revealStagger` from `web/lib/motion.ts`).
- **`AnimatePresence`** wrapping removable items so exit animations run.
- **`layoutId`** for shared-layout morphs (card -> detail).
- **`whileHover` / `whileTap` / `whileFocus`** for micro-interactions (Levels 1-3).
- **`drag` + `dragConstraints` + `inertia`** with `spring.*` presets for physics.

## Rules

- Durations: import `duration` and divide by 1000 (Framer uses seconds).
- Easings: import `easing` arrays; never use the string `"linear"`.
- Animate only `transform`/`opacity` (see `18-performance`).
- Always provide `prefers-reduced-motion` handling via `useReducedMotion()`
  (see `17-accessibility`).

## State machine

Map the 8-state machine (see `05-state-transitions`) to Framer variants:

```tsx
const variants = {
  idle: { ... },
  hover: { ... },   // whileHover
  pressed: { ... }, // whileTap
  loading: { ... },
  success: { ... },
  // focused handled via CSS :focus-visible, disabled via aria-disabled
};
```

## Reference

`web/components/ui/button.tsx` and `metric-card.tsx` show the canonical
Framer Motion usage with tokens.
