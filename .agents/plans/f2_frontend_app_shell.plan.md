# Goal Description
Phase F2 implements the Frontend App Shell within the `web/` application. The primary objective is to lay down the global navigation, repository/reference picker, layout structure, and asynchronous query handling. We will integrate TanStack Query for data fetching, build route stubs for the dashboard, graph, drift, and similar views, and implement robust loading, empty, and error states per frontend guides (rules 13-15).

## Proposed Changes

---

### Dependencies
#### [MODIFY] package.json
- Install `@tanstack/react-query`, `@tanstack/react-query-devtools`, and `axios` via `pnpm add`.

---

### Core Shell Architecture
#### [NEW] web/components/providers.tsx
- Setup a React Server Component to merge Next.js with Client boundaries, provisioning `QueryClientProvider` globally.
- Configure default `staleTime` and global error handling strategies.

#### [NEW] web/context/RepoContext.tsx
- Implement a lightweight React Context or Zustand store that holds the global `repo` path and `ref` (branch) state accessed via `gdss serve`. 

#### [MODIFY] web/app/layout.tsx
- Integrate `Providers` into the RootLayout.
- Wrap application content inside an app shell layout featuring a side navigation bar and top context bar.

---

### App Shell Components
#### [NEW] web/components/navigation.tsx
- Left sidebar presenting links to `/`, `/graph`, `/drift`, and `/similar`.
- Ensure keyboard navigability and accessibility states (per Rule 17).

#### [NEW] web/components/topbar.tsx
- Global top bar displaying the Repo/Ref Context Picker, enabling the user to switch active context parameters.

---

### Route Skeleton & UX Patterns
#### [NEW] web/app/page.tsx (or dashboard/page.tsx)
- Redirect or serve dashboard shell UI utilizing the TanStack Query hook wrapper for `GET /v1/status` and `GET /v1/drift`.

#### [NEW] web/app/graph/page.tsx, web/app/drift/page.tsx, web/app/similar/page.tsx
- Route stubs representing the entry point for independent UI tools.

#### [NEW] web/app/error.tsx
- Next.js root error layout displaying graceful failure states, ensuring widget/page failures do not crash the app (Rule 15).

#### [NEW] web/app/loading.tsx
- Skeleton placeholder preventing CLS (Rule 13) by reserving layout space globally while components initialize.

---

## Verification Plan

### Automated Tests
1. **Frontend Verify Script**: Run `bash harness/verify-frontend.sh` to validate `eslint`, `tsc`, `token_fitness`, and zero-CLS `size-limit` bundler.
2. **Component Tests**: Add Vitest (`web/tests/setup.ts` + `*.test.tsx`) assertions for `Navigation`, checking proper link traversal and `jest-axe` a11y boundaries.

### Manual Verification
1. `gdss serve` API endpoints simultaneously with `cd web && pnpm dev`.
2. Ensure clicking navigation transitions gracefully via Skeletons to route endpoints.
3. Validate "Empty" or "Error" loading paradigms by simulating 404 responses.
