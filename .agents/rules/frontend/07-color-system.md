---
description: Color system for GDSS frontend
globs: web/**
alwaysApply: false
---

# Color System

Colors are **semantic roles**, not raw hex. Raw hex lives ONLY in
`web/lib/tokens.ts`. Components reference roles; themes swap underlying values.

## Roles (from `colors` in tokens)

- Surfaces: `bg`, `surface`, `surfaceElevated`, `surfaceGlass`
- Text: `text`, `textMuted`, `textSubtle`
- Borders: `border`, `borderStrong`
- Accents: `accent`, `accentMuted`, `success`, `warning`, `danger`
- GDSS manifold: `node`, `edge`, `conflict`, `drift`, `trajectory`, `merge`

## Semantic mapping (GDSS-specific)

| Concept     | Color role  | Meaning                          |
| ----------- | ----------- | -------------------------------- |
| conflict    | `danger`    | non-commutativity, needs attention |
| drift       | `warning`   | trajectory diverging from attractor |
| trajectory  | `success`   | healthy committed path            |
| merge       | `merge`     | geodesic convergence             |
| node        | `node`      | a symbol on the manifold         |
| edge        | `edge`      | dependency / data flow           |

## Rules

- Saturated color carries meaning; do not use it decoratively.
- One accent per view as the focal color.
- Maintain WCAG AA contrast (see `17-accessibility`); `textSubtle` is for
  non-essential metadata only.
- Dark-first: GDSS surfaces are deep; reserve light backgrounds for deliberate
  contrast moments.
