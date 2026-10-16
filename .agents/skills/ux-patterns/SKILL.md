---
name: ux-patterns
description: Apply GDSS UX patterns - loading/empty/error states, information hierarchy, progressive disclosure, and feedback affordances. Use when designing user flows, state coverage, or deciding what to show across loading/empty/error/success.
---

# UX Patterns (GDSS)

## State coverage

Every view/component covers loading, empty, error, and success explicitly -
never assume the happy path. See `.cursor/rules/frontend/13-14-15`.

| State   | Pattern                                              |
| ------- | ---------------------------------------------------- |
| loading | local skeleton, zero CLS, cross-fade to data         |
| empty   | teach + primary action (first impression, not error)  |
| error   | WHAT/WHY/FIX + retry; isolate per-widget              |
| success | transient confirmation (overshoot), auto-return     |

## Information hierarchy

```
Hero -> Section -> Card -> Widget -> Content -> Metadata
```

Spacing separates before color does. One focal point per view.

## Progressive disclosure

Show the essential first; reveal detail on demand (expand, drill-down,
command palette). Avoid dumping all metrics at once.

## Feedback affordances

- Every action gives immediate feedback (Level 1-2 motion) even before the
  async result arrives (optimistic UI where safe).
- Loading lives *in* the component (button spinner), not over the page.
- Errors are inline and recoverable; never blank the view for a single failure.

## Anti-patterns

- Full-screen spinner for a single widget.
- Bare "No data".
- Color-only meaning.
- Layout shift on data arrival.
