# gdss-web

The GDSS frontend - the "visual brain" that makes the geometric-semantic
manifold visible. Governed by the frontend harness in `.cursor/rules/frontend/`,
`.cursor/skills/*`, and `harness/sensors/frontend/`.

**Intent:** depict drift, structure, and assistive similarity so teams see merge
risk earlier — not to guarantee perfect working code. See
[`../docs/PRODUCT_INTENT.md`](../docs/PRODUCT_INTENT.md).

## Stack (installed)

- Next.js (App Router) + React + TypeScript
- Tailwind CSS (wired to `lib/tokens.ts`)
- Framer Motion (wired to `lib/motion.ts`)
- class-variance-authority (variants), lucide-react (icons)
- Vitest + Testing Library + jest-axe (component + a11y tests)

## Recommended (install on demand)

| Area              | Package                          |
| ----------------- | -------------------------------- |
| Components        | shadcn/ui + Radix UI             |
| Complex animation | gsap                             |
| 3D                | three + @react-three/fiber       |
| Charts            | d3 or @visx/*                    |
| Node graphs       | reactflow                        |
| Illustrations     | lottie-react                     |
| State             | zustand                          |
| Data fetching     | @tanstack/react-query            |

## Commands

```bash
pnpm install
pnpm dev          # local dev server
pnpm lint         # eslint + jsx-a11y
pnpm typecheck    # tsc --noEmit
pnpm test         # vitest + jest-axe
pnpm build        # next build
pnpm size         # size-limit bundle budget
pnpm playwright   # e2e a11y + CLS (optional)
```

## Definition of done

A frontend change is done only when `bash harness/verify-frontend.sh` is green
(F1 static -> F2 component -> F3 e2e). See `AGENTS.md`.

## Tokens are the single source of truth

No raw `px`/`ms`/hex outside `lib/tokens.ts` and `lib/motion.ts`. Enforced by
`harness/sensors/frontend/token_fitness`.
