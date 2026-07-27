---
description: Motion principles for GDSS frontend
globs: web/**
alwaysApply: false
---

# Motion

Full reference: `.cursor/skills/motion-design/motion.md`. Tokens:
`web/lib/motion.ts`.

## Duration scale (import from `duration`)

```
tiny     100ms   ripple, press snap, toggle tick
secondary 180ms  icon morph, label swap, subtle hover
primary  250ms   hover lift, state change
slow     450ms   appear / disappear (modal, toast)
page     500ms   page transitions, shared-layout morph
```

## Easing (never `linear`)

```
easeOut       entering the screen (decelerate to rest)
easeIn        leaving the screen
easeInOut     between two visible states
spring        physics interactions (drag, toggle, snap)
anticipation  pull back before main motion
overshoot     delightful confirmations
```

## Motion hierarchy by role

```
Primary action    250ms
Secondary         180ms
Tiny feedback     100ms
Page transition   500ms
Background        infinite (ambient, never blocks perception)
```

## Animation hierarchy (Level 0 -> Level 10)

Every animated element must declare its level. Do not animate randomly.

```
0 Nothing moves | 1 Hover | 2 Pressed | 3 Focus | 4 Appear | 5 Disappear
6 State change | 7 Layout | 8 Page | 9 Background | 10 Physics
```

## Animation psychology

People notice **movement before color before text**. Motion guides attention
and explains state change; it is not decoration.

## Reduced motion

Every animated component ships a `prefers-reduced-motion` branch: keep state
changes, drop ambient/physics. Enforced by `token_fitness`.
