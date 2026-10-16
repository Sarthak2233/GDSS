---
name: verify-frontend
description: Run and interpret the GDSS frontend verification gate (harness/verify-frontend.sh) - the three frontend layers F1 static, F2 component, F3 end-to-end. Use when verifying frontend changes or reading frontend gate failures.
---

# Verify Frontend (GDSS)

The frontend gate is the externalized definition of done for `web/`. It mirrors
the backend three-layer hierarchy. Run:

```bash
bash harness/verify-frontend.sh
```

(Also invoked by `harness/verify.sh` when `web/` exists.)

## Layers (each gates the next)

### F1 - static
- **eslint** (+ `eslint-plugin-jsx-a11y`) - lint + accessibility rules.
- **tsc --noEmit** - type checking.
- **token_fitness** - no raw `ms`/`linear`/hex outside token files, no arbitrary
  Tailwind spacing, every interactive component ships a `prefers-reduced-motion`
  branch.

### F2 - component
- **vitest** + **jest-axe** - behavior + accessibility unit/component tests.

### F3 - end-to-end (optional, degrades gracefully)
- **Playwright** smoke running `axe-core` (keyboard nav + a11y) and a CLS
  check (~0 layout shift).
- **size-limit** bundle budget.

## Reading failures

Failures are formatted WHAT/WHY/FIX. Fix the earliest layer first; each layer
gates the next, so a later layer's results may be stale until earlier layers
are green.

## Graceful degradation

If `pnpm`/node/browsers are absent, each sensor **skips** with install
instructions (matching the backend `lint.sh` pattern) rather than failing, so
`harness/verify.sh` stays runnable on a Python-only machine. Install the
tooling to make a sensor a hard gate.

## Fast feedback

Editing `web/**/*.{tsx,ts,css}` triggers `.cursor/hooks/run-fast-frontend-sensors.sh`
(token-lint + eslint on the changed file) for keep-quality-left feedback before
the full gate.

See `AGENTS.md` (frontend definition of done) and `.cursor/rules/frontend/`.
