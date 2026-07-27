---
name: interaction-design
description: Design micro-interactions and the 8-state interaction machine for GDSS components - buttons, toggles, cards, drag, and focus. Use when designing how a component responds to hover/press/focus/loading/success/failure/disabled.
---

# Interaction Design (GDSS)

## The 8-state machine

```
Idle -> Hover -> Focused -> Pressed -> Loading -> Success -> Failure -> Disabled
```

Every interactive component defines its visual response for each reachable
state. Never ad-hoc `if loading: spinner`.

## Micro-interactions

- **Button**: hover -> lift -> shadow -> scale -> cursor -> press -> release ->
  ripple -> success -> disabled.
- **Toggle**: slide -> snap -> glow -> color -> icon morph.
- **Card**: hover -> elevation -> parallax -> gradient -> blur -> shadow.

Use `duration.tiny` for snaps, `duration.primary` for lifts, `easing.overshoot`
only for delightful confirmations.

## Focus

- Visible `:focus-visible` ring (replace, never remove).
- Focus is Level 3 motion; keep it calm and clear.
- Modal: trap focus, restore on close, `Escape` dismisses.

## Drag / physics

- `spring.snap/gentle/bouncy` with `drag` + `dragConstraints` + `inertia`.
- Generous hit areas; clear release affordance.

## Reduced motion

Ship a `prefers-reduced-motion` branch: keep state changes, drop ambient/
physics. See `.cursor/rules/frontend/05-state-transitions` and `17-accessibility`.
