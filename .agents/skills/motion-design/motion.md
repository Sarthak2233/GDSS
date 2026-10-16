# Motion Principles (GDSS visual brain)

This is the canonical reference for animation in GDSS frontend. The code tokens
live in `web/lib/motion.ts`; this document explains the *why* and the *when*.

## Animation psychology

People notice, in order:

```
movement  before  color  before  text
```

Therefore:
- Motion guides attention. It is not decoration.
- Motion explains. A state change should *show* the transition, not snap.
- Motion is reserved for things that must be noticed; ambient motion must stay
  below the threshold of distraction.

## Animation hierarchy (Level 0 -> Level 10)

Every animated element must know its level. Do not animate randomly. Higher
levels are rarer and more expensive (attention + performance).

```
Level 0  Nothing moves
Level 1  Hover
Level 2  Pressed
Level 3  Focus
Level 4  Appear
Level 5  Disappear
Level 6  State change
Level 7  Layout transition
Level 8  Page transition
Level 9  Background animation
Level 10 Physics simulation
```

## Duration scale

```
Fast    100ms   tiny feedback (ripple, press snap, toggle tick)
Medium  250ms   primary action (hover lift, state change)
Slow    450ms   appear / disappear (modal, toast)
Page    500ms   page transitions, shared-layout morph
```

## Easing

Use these, never `linear` (linear feels mechanical/dead):

```
easeOut       things entering the screen (decelerate to rest)
easeIn        things leaving the screen
easeInOut     transitions between two visible states
spring        physics-feeling interactions (drag, toggle, snap)
anticipation  pull back before the main motion
overshoot     delightful micro-interactions (success, confirm)
```

## Motion hierarchy (by role)

```
Primary action    250ms
Secondary         180ms
Tiny feedback     100ms
Page transition   500ms
Background        infinite (ambient, never blocks perception)
```

## The 8-state interaction machine

Every interactive component must define its visual response for each reachable
state instead of ad-hoc `if loading: spinner`:

```
Idle -> Hover -> Focused -> Pressed -> Loading -> Success -> Failure -> Disabled
```

## Micro-interactions

Button: hover -> lift -> shadow -> scale -> cursor -> press -> release -> ripple -> success -> disabled
Toggle: slide -> snap -> glow -> color -> icon morph
Card:   hover -> elevation -> parallax -> gradient -> blur -> shadow

## Component anatomy reveal order

Reveal in this order, staggered (container first, footer last):

```
Container -> Header -> Body -> Actions -> Footer
```

## Reduced motion

Every animated component must ship a `prefers-reduced-motion` branch that
disables non-essential motion (keep state changes, drop ambient/physics). This
is enforced by `harness/sensors/frontend/token_fitness`.

## GDSS-specific motion (the manifold made visible)

GDSS is mathematical; the UI should look mathematical, not like a generic
dashboard. Map concepts to motion:

```
Semantic graph     -> animated graph
Nodes              -> breathe (Level 9 ambient, low amplitude)
Edges              -> pulse (data flowing along the trajectory)
Conflicts          -> glow (non-commutativity demands attention)
Drift              -> moves (trajectory diverges from attractor)
Trajectory         -> animates (integral of tangent vectors)
Merge              -> converges (geodesic path convergence)
```
