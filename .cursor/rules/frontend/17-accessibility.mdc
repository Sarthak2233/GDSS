---
description: Accessibility for GDSS frontend
globs: web/**
alwaysApply: false
---

# Accessibility

Accessibility is non-negotiable and enforced by `harness/sensors/frontend`
(`jest-axe` in component tests, `axe-core` in Playwright).

## Keyboard

- Every interactive element is keyboard reachable and operable.
- Visible `:focus-visible` ring using `accent` (never remove focus outlines;
  if you restyle, replace, don't remove).
- Logical tab order follows visual order; no keyboard traps.
- Modal: focus trap + restore focus on close + `Escape` to dismiss.

## ARIA

- Use semantic HTML first (`button`, `nav`, `dialog`); add ARIA only when
  semantics cannot be expressed natively.
- `aria-disabled` for disabled interactive elements (not just visual opacity).
- `aria-invalid` + `aria-describedby` for form errors (see `15-error-ui`).
- Live regions (`aria-live`) for async status changes (loading/success/error).

## Motion

- Ship a `prefers-reduced-motion` branch for every animated component: keep
  state changes, drop ambient/physics. Enforced by `token_fitness`.
- No auto-playing motion faster than ~3 flashes/sec (seizure safety).

## Contrast

- Body text >= 4.5:1; large text >= 3:1 (WCAG AA).
- Never convey meaning by color alone; pair with text or icon.

## Testing

- Component tests include a `jest-axe` assertion (see
  `web/tests/*.test.tsx`).
- Playwright smoke runs `axe-core` over key routes.
