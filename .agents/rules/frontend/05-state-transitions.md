---
description: State transition system for GDSS frontend components
globs: web/**
alwaysApply: false
---

# State Transitions

Never do ad-hoc `if loading: spinner`. Every interactive component must reason
about the **8-state interaction machine** explicitly.

```
Idle -> Hover -> Focused -> Pressed -> Loading -> Success -> Failure -> Disabled
```

States form a graph, not a strict line, but every component must *define* its
visual response for each reachable state.

## Required per state

| State    | Must define                                  |
| -------- | -------------------------------------------- |
| idle     | resting appearance                           |
| hover    | affordance lift/shadow (Level 1 motion)      |
| focused  | visible focus ring (accessibility, `17-accessibility`) |
| pressed  | scale-down/snap (Level 2, `duration.tiny`)   |
| loading  | non-blocking progress (see `13-loading-states`) |
| success  | transient confirmation (overshoot, then idle) |
| failure  | clear error affordance (see `15-error-ui`)   |
| disabled | reduced opacity, no-hover, `aria-disabled`   |

## Transitions

- Animate *between* states with `duration.primary` + `easeInOut` (state change
  is Level 6).
- Success/Failure are transient: auto-return to idle after ~1.5s unless the
  error is persistent.
- Loading must never jump-cut to content; cross-fade skeleton -> content.

## Reference

`web/components/ui/button.tsx` implements the full 8-state machine and is the
canonical example. Mirror its structure for new components.
