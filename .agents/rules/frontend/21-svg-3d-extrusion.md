---
description: 3dsvg extruded SVG/text for GDSS brand, labels, and manifold visuals
globs: web/**
alwaysApply: false
---

# 3dsvg Extrusion in GDSS Frontend

Use `3dsvg` when you want declarative, DOM-inspectable 3D extrusions of SVG
paths or text in the GDSS frontend. It is ideal for branded hero elements,
extruded branch/symbol labels, and SVG-based building blocks inside the manifold
view. It is **not** a general parametric-surface renderer.

## When to use

- 3D brand/logo or wordmark hero elements.
- Extruded node, branch, or symbol labels inside the manifold view.
- Composing SVG grid/axis/curve art into a larger 3D visualization.
- Cases where raw R3F geometry is overkill but a 3D look is still desired.

## When not to use

- Arbitrary mathematical surfaces or smooth manifold planes (use R3F / shaders
  via rule `19-threejs` and skill `webgl`).
- Large node counts or particle systems (use `InstancedMesh` via `webgl`).
- Flat dashboards, tables, or simple metrics (use React Flow / D3 via rule
  `11-data-visualization`).

## Rules

- **Dynamic import with SSR disabled.** WebGL is browser-only. Always load
  `3dsvg` through `next/dynamic` with `ssr: false`.
- **Lazy load.** Keep `3dsvg` out of the initial bundle; place it inside a
  dynamic route or component chunk.
- **Cap WebGL contexts.** Browsers limit active contexts to ~8–16. Use at most
  3–4 `<SVG3D>` instances per page.
- **Tokens only.** Use `web/lib/tokens.ts` for colors and `web/lib/motion.ts`
  for durations/easings. No raw hex, raw `ms`, or `linear` easing.
- **Reduced-motion fallback.** Every 3D extrusion must ship a static 2D SVG
  fallback when the user prefers reduced motion. Disable `animate`,
  `cursorOrbit`, and drag/scroll orbit in that branch.
- **Reserve space.** Provide explicit `width` and `height` props or a stable
  wrapper to avoid CLS.
- **Bundle budget.** After adding a `3dsvg` route, run `pnpm size`. Keep the
  manifold chunk within the `size-limit` budget in `web/package.json`; justify
  any budget increase.
- **No source bodies / no PII.** 3D labels and textures display metadata only
  (symbol names, branch names). Never embed source code or personal data.
- **Never auto-merge.** Visuals may suggest conflicts or merges, but they must
  never trigger silent resolutions.

## Concept mapping

| GDSS concept | 3dsvg representation |
| ------------ | -------------------- |
| Brand/logo | Extruded SVG with `material="metal"` / `material="glass"` |
| Branch/symbol label | `text` + `font` + `material="emissive"` |
| Node | `color={colors.node}` |
| Edge | `color={colors.edge}` with `material="glass"` |
| Conflict | `color={colors.danger}` with `material="emissive"`; disable pulse under reduced motion |
| Drift | `animate="float"` at low speed |
| Trajectory | `color={colors.trajectory}` |
| Merge | `animate="spinFloat"` only when not reduced motion |

## Minimal pattern

```tsx
import dynamic from "next/dynamic";
import { useReducedMotion } from "framer-motion";
import { colors } from "@/lib/tokens";

const SVG3D = dynamic(
  () => import("3dsvg").then((m) => ({ default: m.SVG3D })),
  { ssr: false }
);

export function Logo3D() {
  const reduced = useReducedMotion();
  if (reduced) {
    return (
      <div className="w-80 h-60 flex items-center justify-center">
        <svg viewBox="0 0 100 100" className="w-full h-full" aria-label="GDSS logo">
          {/* Static 2D fallback art */}
        </svg>
      </div>
    );
  }

  return (
    <SVG3D
      svg="/gdss-logo.svg"
      material="metal"
      color={colors.accent}
      depth={0.6}
      animate="float"
      animateSpeed={0.4}
      width={320}
      height={240}
      interactive
      cursorOrbit
    />
  );
}
```

## Testing expectations

When building components with this rule, follow the `build-frontend-component`
skill:

- Render test passes.
- Reduced-motion branch renders a static fallback.
- `await axe(container)` reports no violations.
- `pnpm size` stays within budget.

## Related

- `.cursor/skills/svg-3d-extrusion` — full 3dsvg API and patterns.
- `.cursor/skills/webgl` — raw R3F scenes and shaders.
- `.cursor/skills/svg-animation` — 2D SVG motion and fallback patterns.
- `.cursor/skills/data-visualization` — manifold concept mapping.
- `.cursor/rules/frontend/19-threejs.mdc` — R3F manifold rules.
- `.cursor/rules/frontend/11-data-visualization.mdc` — data-viz rules.
- `.cursor/rules/frontend/18-performance.mdc` — lazy loading and budgets.
- `.cursor/rules/frontend/17-accessibility.mdc` — reduced motion and a11y.
