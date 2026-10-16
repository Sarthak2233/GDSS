---
description: Visual hierarchy principles for GDSS frontend
globs: web/**
alwaysApply: false
---

# Visual Hierarchy

Spacing communicates hierarchy **before** color. The eye should read structure
from whitespace alone; color reinforces it.

## Information hierarchy

```
Hero -> Section -> Card -> Widget -> Content -> Metadata
```

Space between levels grows; Metadata gets the least surrounding space.

## Hierarchy tools, in priority order

1. **Size** - the strongest signal. One hero per view.
2. **Spacing** - groups and separates before color does.
3. **Weight** - `fontWeight.semibold` for headings, `regular` for body.
4. **Color** - `text` vs `textMuted` vs `textSubtle` (see `07-color-system`).
5. **Motion** - reserved for what must be noticed (Level 1-6).

## Anti-patterns

- Everything bold -> nothing is bold.
- Many saturated colors competing -> no focal point.
- Equal spacing everywhere -> no grouping.
- Animating many things at once -> no attention target.

## Density

GDSS is an instrument: lean toward higher density than a consumer app, but use
`textMuted`/`textSubtle` to de-emphasize rather than shrinking below readable
sizes.
