---
name: gsap
description: Use GSAP for complex, choreographed, or scroll-driven animations in GDSS beyond Framer Motion's scope - timelines, ScrollTrigger, and SVG morph. Use when building complex sequenced animations or scroll-driven storytelling in web/.
---

# GSAP (GDSS)

GSAP is for **complex, choreographed, or scroll-driven** animation that
exceeds Framer Motion's variant model: multi-step timelines, ScrollTrigger
storytelling, fine-grained SVG path morphing.

## When to use GSAP vs Framer Motion

- Framer Motion: component-level micro-interactions, enter/exit, shared layout
  (the default).
- GSAP: long choreographed sequences, ScrollTrigger, complex SVG morphs,
  physics-precise timelines.

## Rules

- Use GSAP **only** where Framer Motion is insufficient - don't mix both for
  the same element (double-render conflicts).
- Clean up tweens/timelines/ScrollTriggers in effect cleanup to avoid leaks.
- Respect `prefers-reduced-motion`: gate ScrollTrigger scrub and ambient
  timelines behind `matchMedia`.
- Animate `transform`/`opacity`; avoid layout-triggering properties.
- Keep timelines in custom hooks (`web/lib/gsap/*.ts`) for reuse and testing.

## Performance

- `will-change: transform` on animated elements, removed after.
- Avoid `gsap.to` on `width/height/top/left`.
- Cap simultaneous timelines; pause off-screen.

See `.cursor/rules/frontend/04-animation` and `18-performance`.
