---
name: component-composition
description: Compose small, token-driven, state-machine-complete, accessible frontend components. Use when building new UI components in web/components, defining variants, or structuring component anatomy.
---

# Component Composition (GDSS)

## Anatomy

```
Container -> Header -> Body -> Actions -> Footer
```

Reveal staggered in that order. Not every component needs all five, but if
present they appear in this order.

## The build loop

1. Define the **8-state** response (see `05-state-transitions`).
2. Choose **variants** (intent x size) via a variant helper (`cva`), not nested
   ternaries.
3. Pull all spacing/color/motion from **tokens**; no raw values.
4. Make it **keyboard accessible** + `aria-disabled`/`aria-invalid` as needed.
5. Add a **`prefers-reduced-motion`** branch.
6. Write a **component test** (vitest + jest-axe) asserting behavior + a11y.

## Rules

- Small, composable primitives composed into surfaces - no mega-components.
- Narrow, typed prop surfaces; prefer discriminated unions over loose strings.
- State-machine complete; never ad-hoc `if loading: spinner`.
- Accessible by default: keyboard reachable, `:focus-visible` ring, ARIA only
  when semantics can't be expressed natively.

## Reference

- `web/components/ui/button.tsx` - 8-state machine, tokens, reduced-motion.
- `web/components/ui/metric-card.tsx` - dashboard anatomy + animation.

Mirror their structure for new components. See
`.cursor/rules/frontend/09-component-composition`.
