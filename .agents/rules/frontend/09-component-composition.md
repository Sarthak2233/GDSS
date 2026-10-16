---
description: Component composition for GDSS frontend
globs: web/**
alwaysApply: false
---

# Component Composition

## Component anatomy

Every component has this structure:

```
Container -> Header -> Body -> Actions -> Footer
```

Not every component needs all five, but if it has them, they appear in this order
and reveal staggered (see `04-animation`).

## Composition rules

- **Small, composable, token-driven.** Compose small primitives into larger
  surfaces; do not build one-off mega-components.
- **Props are the API.** Keep prop surfaces narrow and typed. Prefer
  discriminated unions for variants over loose string props.
- **Tokens over literals.** Spacing/color/motion come from tokens; no raw
  values (enforced by `token_fitness`).
- **State-machine complete.** Interactive components handle all 8 states (see
  `05-state-transitions`).
- **Accessible by default.** Keyboard reachable, focus-visible, ARIA where
  needed (see `17-accessibility`).

## Variants

Use a variant helper (e.g. `cva`) keyed by intent (`primary`, `secondary`,
`ghost`, `danger`) and size (`sm`, `md`, `lg`). Do not branch styling with
nested ternaries.

## Reference implementations

- `web/components/ui/button.tsx` - 8-state machine, tokens, reduced-motion.
- `web/components/ui/metric-card.tsx` - dashboard anatomy + animation.

Mirror their structure when adding new components.
