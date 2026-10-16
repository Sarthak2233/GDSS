---
name: motion-design
description: Design motion for GDSS frontend - animation hierarchy (Level 0-10), duration/easing/motion-hierarchy, animation psychology, and the 8-state interaction machine. Use when animating any UI element, choosing durations/easings, or designing micro-interactions and state transitions.
---

# Motion Design (GDSS)

Motion is not decoration; it explains. People notice movement before color
before text, so motion guides attention and clarifies state change.

The canonical reference is [motion.md](motion.md). Tokens live in
`web/lib/motion.ts`. Rules enforced by `harness/sensors/frontend/token_fitness`.

## The loop

1. Identify the element's **animation level** (Level 0-10). Do not animate
   randomly.
2. Pick a **duration** from the scale (`tiny/secondary/primary/slow/page`).
3. Pick an **easing** (`easeOut` entering, `easeIn` leaving, `easeInOut`
   between visible states, `spring` for physics). Never `linear`.
4. Define the **8-state** response (idle/hover/focused/pressed/loading/
   success/failure/disabled).
5. Add a **`prefers-reduced-motion`** branch.
6. Animate only `transform`/`opacity`.

## Animation psychology

```
movement  before  color  before  text
```

- Motion guides attention.
- Motion explains state change (show the transition, don't snap).
- Reserve motion for what must be noticed; ambient stays below distraction.

## Animation hierarchy

```
0 Nothing | 1 Hover | 2 Pressed | 3 Focus | 4 Appear | 5 Disappear
6 State change | 7 Layout | 8 Page | 9 Background | 10 Physics
```

## Motion hierarchy by role

```
Primary action 250ms | Secondary 180ms | Tiny feedback 100ms
Page 500ms | Background infinite
```

## Component anatomy reveal

Stagger in order: Container -> Header -> Body -> Actions -> Footer. Use
`revealStagger` from `web/lib/motion.ts`.

## GDSS manifold motion

Nodes breathe, edges pulse, conflicts glow, drift moves, trajectory animates,
merge converges. See `.cursor/rules/frontend/11-data-visualization`.
