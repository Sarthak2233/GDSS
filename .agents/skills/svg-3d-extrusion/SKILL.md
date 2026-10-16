---
name: svg-3d-extrusion
description: Use 3dsvg to extrude SVGs/text into 3D for GDSS brand elements, node labels, and manifold-plane building blocks in web/.
---

# 3D SVG Extrusion with `3dsvg` (GDSS)

Use the `3dsvg` library (https://github.com/renatoworks/3dsvg) when you need
crisp, declarative 3D extrusions of SVG paths or text inside the GDSS frontend.
It renders through Three.js / React Three Fiber, but exposes a single
component-driven API that is easier to reason about than raw R3F geometry for
branded or label-like 3D content.

## What 3dsvg is and is not

`3dsvg` is a React component that turns SVG markup or text strings into
extruded 3D meshes. It is **not** a general parametric-surface renderer. It
cannot directly render a smooth mathematical manifold plane from arbitrary
geometry data. It can, however, extrude:

- Logo/wordmark SVGs into 3D hero elements.
- Branch names, symbol IDs, or short labels into 3D text inside the manifold
  view.
- SVG-based grid/axis/curve art that can be composed into a larger manifold
  visualization.

For true parametric surfaces or large particle/node clouds, use the `webgl`
skill and rule `19-threejs` instead.

## Installation

Install the package plus its peer dependencies. The engine requires React ≥18,
Three ≥0.160.0, React Three Fiber ≥9, and Drei ≥9.

```bash
cd web
pnpm add 3dsvg three @react-three/fiber @react-three/drei
pnpm add -D @types/three
```

Add `3dsvg` to `transpilePackages` in `next.config.mjs`:

```js
const nextConfig = {
  transpilePackages: ["3dsvg"],
};
export default nextConfig;
```

## Public API

### Main component

```tsx
import { SVG3D } from "3dsvg";
```

Core props:

| Prop | Type | Default | Purpose |
| ---- | ---- | ------- | ------- |
| `text` | `string` | — | 3D text content |
| `font` | `string` | `"DM Sans"` | Google Font name |
| `svg` | `string` | — | Raw SVG markup, local path, or remote URL |
| `depth` | `number` | `1` | Extrusion depth |
| `smoothness` | `number` | `0.2` | Bevel smoothness |
| `color` | `string` | `"#ffffff"` | Base color |
| `material` | `MaterialPreset` | `"default"` | Preset material |
| `metalness` / `roughness` / `opacity` / `wireframe` | `number` / `boolean` | — | Material overrides |
| `texture` | `string` | — | Image URL for texture |
| `lightPosition` | `[x,y,z]` | `[5,8,5]` | Key light position |
| `lightIntensity` / `ambientIntensity` / `shadow` | — | — | Lighting controls |
| `rotationX` / `rotationY` / `zoom` / `fov` | — | — | Camera/scene controls |
| `interactive` / `cursorOrbit` / `orbitStrength` / `draggable` / `scrollZoom` / `resetOnIdle` / `resetDelay` | — | — | Interaction |
| `animate` | `"none" \| "spin" \| "float" \| "pulse" \| "wobble" \| "spinFloat" \| "swing"` | `"none"` | Loop animation |
| `animateSpeed` / `animateReverse` | — | — | Animation tuning |
| `intro` | `"zoom" \| "fade" \| "none"` | `"zoom"` | Entrance animation |
| `introDuration` / `introFrom` / `introTo` | — | — | Intro tuning |
| `width` / `height` / `background` / `className` | — | — | Layout |
| `onReady` / `onAnimationComplete` / `onLoadingChange` | — | — | Lifecycle callbacks |

Material presets: `default`, `plastic`, `metal`, `glass`, `rubber`, `chrome`,
`gold`, `clay`, `emissive`, `holographic`.

### Subpath exports

```tsx
import { SVG3DScene, ExtrudedSVG, useExtrudedGeometry } from "3dsvg/scene";
import { IntroAnimation, LoopAnimation, SmoothControls } from "3dsvg/controls";
import { materialPresets, resolveMaterial } from "3dsvg/materials";
import { useFont, textToSvg } from "3dsvg/use-font";
import type { SVG3DProps, MaterialPreset, MaterialSettings } from "3dsvg/types";
```

Use these when you need lower-level control (custom scene composition, custom
loop animation, material resolution, or font-to-SVG conversion).

## GDSS use cases

### A — 3D brand / logo hero

Extrude a GDSS logo SVG or wordmark text as a branded hero element.

```tsx
import dynamic from "next/dynamic";

const SVG3D = dynamic(
  () => import("3dsvg").then((m) => ({ default: m.SVG3D })),
  { ssr: false }
);

export function GdssLogo3D() {
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

### B — Extruded node / branch labels

Render branch names or symbol IDs as 3D text inside the manifold view. Keep
labels short; long identifiers hurt readability when extruded.

```tsx
export function BranchLabel3D({ name }: { name: string }) {
  return (
    <SVG3D
      text={name}
      font="DM Sans"
      material="emissive"
      color={colors.node}
      depth={0.3}
      animate="none"
      width={200}
      height={80}
      interactive={false}
    />
  );
}
```

### C — Manifold plane building block

A true projected manifold plane is not built-in. Use 3dsvg to extrude SVG
grid/axis/curve art, then compose it with projection math that maps backend
geometry onto the scene once `phase7-research` (`gdss/geometry/`) is ready.

```tsx
// Hypothetical future component; projection math lives in web/lib/manifold-projection.ts
export function ManifoldPlane3D({ projectionSvg }: { projectionSvg: string }) {
  return (
    <SVG3D
      svg={projectionSvg}
      material="glass"
      color={colors.edge}
      depth={0.15}
      animate="none"
      width={600}
      height={400}
      interactive
    />
  );
}
```

## Rules

- **SSR safety:** always import `3dsvg` through `next/dynamic` with
  `ssr: false`. WebGL is browser-only.
- **Lazy loading:** keep `3dsvg` out of the initial bundle. Lazy-load the
  component or route that uses it.
- **WebGL context budget:** browsers limit active WebGL contexts to roughly
  8–16. Cap `<SVG3D>` instances to 3–4 per page.
- **Tokens only:** pull colors from `web/lib/tokens.ts` and durations/easings
  from `web/lib/motion.ts`. Never use raw hex, raw `ms`, or `linear` easing.
- **Reduced motion:** every 3D extrusion must provide a static 2D SVG fallback
  when the user prefers reduced motion. Disable `animate` and `cursorOrbit` in
  that branch.
- **CLS avoidance:** always provide explicit `width` and `height` props or a
  stable wrapper with reserved space.
- **Bundle budget:** after adding `3dsvg`, run `pnpm size`. If the manifold
  route chunk exceeds its budget, split it into a separate dynamic route and/or
  raise the budget with justification in `web/package.json`.
- **No source bodies / no PII:** 3D labels and textures must only display
  metadata (symbol names, branch names). Never embed source code or personal
  data in SVG/text props.
- **Never auto-merge:** 3D visuals may suggest conflicts or merges, but they
  must never trigger silent resolutions.

## Token mapping

| GDSS concept | Token | 3dsvg prop suggestion |
| ------------ | ----- | --------------------- |
| Accent / brand | `colors.accent` | `color` |
| Node | `colors.node` | `color` |
| Edge | `colors.edge` | `color` with `material="glass"` |
| Conflict | `colors.danger` | `color` with `material="emissive"` |
| Drift | `colors.drift` | `color` with `animate="float"` |
| Trajectory | `colors.trajectory` | `color` |
| Merge | `colors.merge` | `color` with `animate="spinFloat"` (if not reduced motion) |
| Intro duration | `duration.slow` | `introDuration` (convert ms → s) |
| Animation speed | `duration.primary` | `animateSpeed` tuning |

## Reduced-motion fallback pattern

```tsx
import { useReducedMotion } from "framer-motion";

export function SafeSVG3D(props: SVG3DProps) {
  const reduced = useReducedMotion();
  if (reduced) {
    return (
      <div style={{ width: props.width, height: props.height }}>
        {/* Static 2D SVG fallback */}
        {props.svg ? <div dangerouslySetInnerHTML={{ __html: props.svg }} /> : <span>{props.text}</span>}
      </div>
    );
  }
  return <SVG3D {...props} />;
}
```

## Testing

When you later build components with this skill, follow the
`build-frontend-component` workflow:

1. Write a failing vitest + jest-axe test first.
2. Assert the component renders, respects reduced motion, and has no axe
   violations.
3. Mock `next/dynamic` if needed, but prefer testing the static fallback path
   directly.
4. Run `bash harness/verify-frontend.sh` until F1/F2/F3 are green.

## Related skills and rules

- `.cursor/skills/webgl` — for raw R3F scenes, shaders, and instancing.
- `.cursor/skills/svg-animation` — for 2D SVG motion and fallback patterns.
- `.cursor/skills/data-visualization` — for manifold concept mapping.
- `.cursor/skills/build-frontend-component` — for the test-first component loop.
- `.cursor/rules/frontend/19-threejs.mdc` — R3F manifold rules.
- `.cursor/rules/frontend/11-data-visualization.mdc` — manifold visual mapping.
- `.cursor/rules/frontend/18-performance.mdc` — lazy loading and bundle budgets.
- `.cursor/rules/frontend/17-accessibility.mdc` — reduced motion and a11y.
