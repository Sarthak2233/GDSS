---
description: Layout principles for GDSS frontend
globs: web/**
alwaysApply: false
---

# Layout

## Grid and rhythm

- Base rhythm is 4px (see `spacing` in `web/lib/tokens.ts`).
- Use the spacing scale for all gaps, padding, margins. No arbitrary values.
- Page layout: 12-column grid on desktop, collapsing to single column on mobile
  (see `16-mobile`).

## Information hierarchy via layout

```
Hero -> Section -> Card -> Widget -> Content -> Metadata
```

Spacing *between* levels grows, so the eye reads hierarchy before reading color.
A Hero gets the most surrounding space; Metadata gets the least.

## Alignment

- One primary alignment axis per section. Don't mix center and left in the same
  row without intent.
- Numbers in tables/dashboards are right-aligned; labels left-aligned.

## Density

GDSS is an instrument; lean toward higher information density than a consumer
app, but never sacrifice legibility. Use `textMuted`/`textSubtle` to de-emphasize
without shrinking below readable sizes.

## Layout shift

Never cause cumulative layout shift (CLS). Reserve space for async content
(skeletons, fixed-aspect containers) before data arrives. Enforced at
`harness/sensors/frontend` (Playwright CLS check).
