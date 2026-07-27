---
description: Loading states for GDSS frontend
globs: web/**
alwaysApply: false
---

# Loading States

Never block perception with a single full-screen spinner. Loading must be
local, informative, and reserve layout space (zero CLS).

## Hierarchy of loading affordances

1. **Skeleton** - preferred for content areas; mirrors final layout, reserves
   space, zero CLS.
2. **Inline progress** - for deterministic operations (a known %).
3. **Spinner** - last resort, only for tiny/indeterminate actions (e.g. a button
   submit), and only inside the component, not over the page.

## Rules

- Reserve the final size before data arrives (fixed-aspect containers,
   skeleton shapes). No layout shift.
- Cross-fade skeleton -> content over `duration.primary`; never jump-cut.
- Loading is a state in the 8-state machine (see `05-state-transitions`); a
  button shows its own loading affordance, not a page-level spinner.
- Keep loading motion subtle (Level 4 appear), not distracting.
- Provide `prefers-reduced-motion`: replace shimmer with a static muted block.

## Anti-patterns

- Full-screen spinner blocking the whole app for a single widget.
- Layout that shifts when content arrives (CLS > 0 fails the gate).
- A spinner with no indication of *what* is loading.
