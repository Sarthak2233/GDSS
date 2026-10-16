---
name: build-frontend-component
description: Test-first workflow for building a GDSS frontend component that is token-driven, state-machine-complete, accessible, and reduced-motion-aware. Use when creating any new UI component in web/components/.
---

# Build a Frontend Component (GDSS)

Mirror the backend TDD loop: behavior + accessibility first, then
implementation, then the harness gate decides "done".

## The loop

1. **Name the component and its states.** List which of the 8 states it must
   handle (idle/hover/focused/pressed/loading/success/failure/disabled). Not all
   components need all eight - but you must *decide*.

2. **Write the failing test first** (vitest + Testing Library + jest-axe).
   Assert behavior through the rendered output and an a11y assertion:
   ```ts
   expect(await axe(container)).toHaveNoViolations();
   ```
   Test: renders, keyboard operable, focus-visible present, loading state
   shows an inline affordance (not a page spinner), reduced-motion path exists.

3. **Implement minimally** to pass, pulling all spacing/color/motion from
   `web/lib/tokens.ts` and `web/lib/motion.ts`. No raw values.

4. **Add the `prefers-reduced-motion` branch** via `useReducedMotion()`.

5. **Run the frontend gate:**
   ```bash
   bash harness/verify-frontend.sh
   ```
   F1 (eslint + tsc + token_fitness) -> F2 (vitest + jest-axe) -> F3 (Playwright
   a11y/CLS + size-limit). Each layer gates the next.

6. **Green = done.** "Code is written" is never sufficient (see `AGENTS.md`).

## Rules

- Anatomy: Container -> Header -> Body -> Actions -> Footer; reveal staggered.
- Variants via `cva` (intent x size), not nested ternaries.
- Animate only `transform`/`opacity`.
- Accessible by default: semantic HTML, `:focus-visible`, ARIA only when needed.

## Reference

`web/components/ui/button.tsx` (full 8-state machine) and
`metric-card.tsx` (dashboard anatomy). Mirror their structure.

See `.cursor/rules/frontend/09-component-composition` and `05-state-transitions`.
