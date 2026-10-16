---
description: Mobile / responsive motion for GDSS frontend
globs: web/**
alwaysApply: false
---

# Mobile

GDSS is primarily a desktop instrument, but must degrade gracefully to tablet
and mobile.

## Responsive layout

- 12-column grid on desktop -> single column on mobile (see `02-layout`).
- Touch targets >= 44x44px (Apple HIG) / 48x48dp (Android).
- No hover-dependent affordances on touch - hover is a *bonus*, not a
  requirement to use a control.

## Responsive motion

- Disable parallax and cursor-tracking effects on mobile (no pointer, and
  gyro/scroll parallax causes motion sickness).
- Reduce ambient animation amplitude on small screens (less screen, less
  budget for distraction).
- Respect `prefers-reduced-motion` always (see `17-accessibility`).

## Performance on mobile

- Mobile has weaker GPUs; cap simultaneous animated elements and avoid
  `backdrop-filter` on mobile (see `10-glassmorphism`, `18-performance`).
- Bundle budgets are tighter on mobile networks (see `size-limit`).

## Gestures

- Use native scroll momentum; do not hijack scroll for "creative" effects.
- Drag interactions (see `04-animation` physics) need generous hit areas and
  clear release affordances.
