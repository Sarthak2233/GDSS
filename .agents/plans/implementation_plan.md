# Implementation Plan: Frontend Alignment with GDSS Backend & UI Fixes

## Goal Description
Align the GDSS frontend interface (`web/`) with the backend deterministic architecture (`gdss/`), eliminate conceptual misinterpretations between research-track differential geometry and production discrete operator algebra, expand the PR Collision Radar ($\Omega_{ij}$) to integrate all available branches (local and remote-tracking/PRs), fix LaTeX compatibility across all documentation and UI components, and resolve the UI bug on `localhost:3000/drift` where the manifold guide and telemetry cards behave erratically or appear blank.

---

## Mathematical Foundations & Notational Reference

To eliminate ambiguity between research-track differential geometry and GDSS's production deterministic engine, all mathematics in GDSS are defined below using standard, KaTeX-safe notation without unescaped underscores.

### 1. The Reference Attractor ($R$)
In GDSS, the base branch (typically `main`) is designated as the **Attractor** ($R$). It represents the canonical stable state of the repository. All feature branches originate from $R$ at a common fork point (merge base) and are expected to converge back to $R$.

### 2. Semantic Branch Drift: $I(B_i)$
The drift metric measures how far a feature branch $B_i$ has diverged from the attractor $R$. It combines point-in-time semantic difference with cumulative historical churn:

$$ I(B_i) = \alpha \cdot d_{\mathrm{tip}}(B_i, R) + \beta \cdot I_{\mathrm{traj}}(B_i) $$

Where:
- $d_{\mathrm{tip}}(B_i, R) \in [0, 1]$: Cosine distance between symbol embedding representations at branch tip $B_i$ and attractor tip $R$.
- $I_{\mathrm{traj}}(B_i) \in [0, 1]$: Cumulative trajectory path integral measuring the volume of AST transformation operators applied between merge base and tip:
  $$ I_{\mathrm{traj}}(B_i) = \min\left(1.0, \frac{1}{K} \sum_{k=1}^m \|\Delta \mathrm{AST}_k\|\right) $$
- Default calibration weights: $\alpha = 0.40$ (current distance), $\beta = 0.60$ (historical transform volume).

### 3. Drift Velocity ($v_i$) and Convergence Dynamics
Drift velocity measures whether a branch is moving toward or away from the attractor over successive commits:

$$ v_i = \frac{\Delta I(B_i)}{\Delta t} = \frac{I(B_i, t_{\mathrm{now}}) - I(B_i, t_{\mathrm{prev}})}{t_{\mathrm{now}} - t_{\mathrm{prev}}} $$

- **$v_i < 0$ (Converging):** The branch is syncing with base or reconciling differences.
- **$v_i = 0$ (Stable):** Divergence magnitude is stationary.
- **$v_i > 0$ (Diverging):** The branch is actively accumulating new modifications away from base.

### 4. Commutativity Lie Bracket: $[T_i, T_j]$
Let $T_i$ and $T_j$ be the sets of AST transformations introduced by branch $B_i$ and branch $B_j$ respectively. Two transformations commute if their execution order does not alter the resulting AST state:

$$ [T_i, T_j] = T_i \circ T_j - T_j \circ T_i $$

- $[T_i, T_j] = 0$: **Commutative Equilibrium.** The branches touch orthogonal symbols or independent files. They can be merged in any order with zero semantic interference.
- $[T_i, T_j] \ne 0$: **Non-Commutative Collision.** At least one pair of operations conflicts (e.g., Branch A modifies a function signature while Branch B calls the previous signature, or Branch A modifies a file while Branch B deletes it).

### 5. Pairwise PR Collision Tensor: $\Omega_{ij}$
For $N$ concurrent branches $\{B_1, B_2, \dots, B_N\}$, GDSS constructs an $N \times N$ symmetric collision matrix $\Omega$. Each entry $\Omega_{ij}$ quantifies the pairwise merge hazard between branch $i$ and branch $j$:

$$ \Omega_{ij} = w_{\mathrm{file}} S_{\mathrm{file}} + w_{\mathrm{func}} S_{\mathrm{func}} + w_{\mathrm{sym}} S_{\mathrm{sym}} + w_{\mathrm{dep}} S_{\mathrm{dep}} + w_{\mathrm{interfere}} \mathcal{I} $$

Where each term is a normalized factor in $[0, 1]$:
1. **$S_{\mathrm{file}}(i, j) \in \{0, 1\}$:** File overlap indicator (1 if $B_i$ and $B_j$ modify any common file path). Weight $w_{\mathrm{file}} = 0.20$.
2. **$S_{\mathrm{func}}(i, j) \in \{0, 1\}$:** Function/class modification clash indicator (1 if both branches modify or delete the same function or class). Weight $w_{\mathrm{func}} = 0.50$.
3. **$S_{\mathrm{sym}}(i, j) \in \{0, 1\}$:** AST symbol contract overlap indicator (1 if target symbol names intersect). Weight $w_{\mathrm{sym}} = 0.70$.
4. **$S_{\mathrm{dep}}(i, j) \in \{0, 1\}$:** Call-graph dependency overlap (1 if the transitive blast radii of $B_i$ and $B_j$ intersect in the semantic graph). Weight $w_{\mathrm{dep}} = 0.40$.
5. **$\mathcal{I}(i, j) \in [0, 1]$:** Non-commutative operator interference ratio:
   $$ \mathcal{I}(i, j) = \frac{\text{Count of non-commuting operator pairs}}{\max(1, \text{Total contact operator pairs})} $$
   Weight $w_{\mathrm{interfere}} = 0.30$.

The result is clamped to $\Omega_{ij} \in [0, 1]$. The diagonal entries represent branch self-energy derived from drift magnitude: $\Omega_{ii} = \min(1.0, I(B_i))$.

The overall repository merge risk is the sum of unique pairs:
$$ \mathcal{R}_{\mathrm{merge}} = \sum_{1 \le i \le j \le N} \Omega_{ij} $$

---

## User Review Required

> [!IMPORTANT]
> **1. Multi-Branch Discovery Scope for Collision Tensor $\Omega_{ij}$:**
> - Currently, `observer.list_local_branches()` discovers only local Git heads. When developers clone or checkout a single branch, only `main` and `new_mig` exist locally, resulting in a single active branch against $R$ ($N=1$) and zero pairwise off-diagonal entries.
> - **Proposal:**
>   - Add `GitObserver.list_all_branches(include_remotes=True)` to discover both local branches and remote tracking branches (`origin/*` / PR heads).
>   - Provide a clean UI selector on `/tensor`: `[All Concurrent Branches (Local + Remote)]` vs `[Local Only]`.
>   - When $N = 1$, instead of showing a blank/confusing "No entries" card, show the branch's self-energy alongside a 1-to-base comparison against the attractor's unmerged commits, with explicit instructions on fetching remote PR branches (`git fetch origin`).

> [!IMPORTANT]
> **2. Re-Framing Abstract Research Jargon into Concrete Engineering Realities:**
> - The frontend currently contains romanticized theoretical physics terms: *"Geodesic Orbital Radar"*, *"Attractor $\gamma_0(t)$"*, *"Geodesic Energy Gauge"*.
> - As defined in [`AGENTS.md`](file:///home/sarakb/projects/GDSS/AGENTS.md) and [`PRODUCT_SPEC.md`](file:///home/sarakb/projects/GDSS/PRODUCT_SPEC.md), Riemannian differential geometry ($G$, $P$) is **Phase R (Research Track)**. The production system is a **discrete AST and graph transform engine** running locally at **$0 token cost**.
> - **Proposal:** Keep the engaging orbital visualization, but update all labels and guides to clearly present the discrete mathematics:
>   - Label the radar: *"Phase-Plane Trajectory Radar (2D Projection of AST Churn)"*.
>   - Label the energy gauge: *"Drift Magnitude $I(B)$"*.
>   - Ground the guide accordion directly in the 5 collision terms and the Lie bracket commutativity rules.

---

## Proposed Changes

### Component 1: Fix Drift Monitor UI & Guide Disappearance (`web/app/(dashboard)/drift/page.tsx`)

#### [MODIFY] [`web/app/(dashboard)/drift/page.tsx`](file:///home/sarakb/projects/GDSS/web/app/%28dashboard%29/drift/page.tsx)
- **Container Layout**: Change `className="flex flex-col h-full space-y-6"` to `min-h-full` to prevent flex children clipping and layout collapses inside the dashboard's `overflow-auto` container.
- **Accordion State Preservation**: Ensure `showManifoldGuide` is resilient across query refetches.
- **Guide Content Revision**: Re-write the collapsible guide with clear, developer-friendly mathematical explanations:
  - Explain Attractor $R$, Tip distance vs Trajectory integral, Velocity sign ($v \le 0$ converging, $v > 0$ diverging), and how drift leads into the collision tensor $\Omega_{ij}$.
- **Query Loading Behavior**: Set `placeholderData: (prev) => prev` in TanStack Query so the page does not flash back to empty skeleton rectangles on background polling refetches.

#### [MODIFY] [`web/components/drift/severity-alerts-matrix.tsx`](file:///home/sarakb/projects/GDSS/web/components/drift/severity-alerts-matrix.tsx)
- **Eliminate Contradictory Empty State**: When `alerts.length === 0`, do NOT render `<DriftEmptyState />` (which asserts "no drift detected" even when branches have active drift).
- Replace with a concise status banner:
  *"No critical or high-severity alerts triggered for current drift thresholds. Active trajectories remain within acceptable divergence limits."*

---

### Component 2: Backend API Optimization & Remote Branch Discovery

#### [MODIFY] [`gdss/watcher/git_observer.py`](file:///home/sarakb/projects/GDSS/gdss/watcher/git_observer.py)
- Implement `list_all_available_branches(include_remotes: bool = True) -> list[str]` to discover both local heads and remote tracking branches (`origin/*`), stripping duplicate prefixes cleanly while preserving branch disambiguation.

#### [MODIFY] [`gdss/api/service.py`](file:///home/sarakb/projects/GDSS/gdss/api/service.py)
- **Memoize `get_alerts`**: Apply commit-SHA memoization to `get_alerts` (using `_ALERTS_SERVICE_CACHE`), matching `get_drift`. This eliminates the 8–20s blocking latency that kept the drift page stuck in skeleton loading.
- **Extend `get_tensor`**: Accept an optional `include_remotes: bool = False` or explicit list of branch targets.
- **Extend `get_branches`**: Return `{ local_branches: [...], all_branches: [...], active_branch: ... }`.

---

### Component 3: Conflict Tensor ($\Omega_{ij}$) Multi-Branch Formation & Interactive Explorer

#### [MODIFY] [`web/app/(dashboard)/tensor/page.tsx`](file:///home/sarakb/projects/GDSS/web/app/%28dashboard%29/tensor/page.tsx)
- **Branch Scope Toggle**: Add a filter bar: `[All Active Branches (Local + Remote)]` vs `[Local Branches Only]`.
- **Explainable $\Omega_{ij}$ Formation**:
  - When $N \ge 2$: Render the full $N \times N$ heatmap with cell-by-cell inspection.
  - When $N = 1$: Render the single-branch self-energy and provide an Attractor-Collision inspection comparing branch changes against any unmerged commits on the attractor.
- **Detailed Term Breakdown Card**: When a cell $(i, j)$ is selected, display the exact 5-term mathematical breakdown:
  - $w_{\mathrm{file}} \cdot S_{\mathrm{file}} = 0.20 \times [0 \text{ or } 1]$
  - $w_{\mathrm{func}} \cdot S_{\mathrm{func}} = 0.50 \times [0 \text{ or } 1]$
  - $w_{\mathrm{sym}} \cdot S_{\mathrm{sym}} = 0.70 \times [0 \text{ or } 1]$
  - $w_{\mathrm{dep}} \cdot S_{\mathrm{dep}} = 0.40 \times [0 \text{ or } 1]$
  - $w_{\mathrm{interfere}} \cdot \mathcal{I} = 0.30 \times [0.0 \dots 1.0]$
  - Total $\Omega_{ij}$ and list of active reasons.

#### [MODIFY] [`web/components/tensor/omega-heatmap.tsx`](file:///home/sarakb/projects/GDSS/web/components/tensor/omega-heatmap.tsx)
- Ensure all LaTeX math in descriptions and headers uses valid notation.
- Add cell tooltips displaying the exact numeric score and primary collision reason.

---

### Component 4: Two-Brain Architecture & Telemetry Transparency

#### [MODIFY] [`web/components/navigation.tsx`](file:///home/sarakb/projects/GDSS/web/components/navigation.tsx) & Layout
- Add a subtle status pill in the sidebar/navigation:
  `Deterministic Core: Active ($0 Tokens)`
- Ensure each dashboard view clearly labels whether results are derived from the **Deterministic Brain** (AST transforms, graph proof) or the **Probabilistic Brain** (assistive vector embeddings and LLM convergence suggestions).

---

## Verification Plan

### Automated Tests
1. **Backend Sensor & Gate Verification**:
   ```bash
   bash harness/sensors/lint.sh
   bash harness/sensors/typecheck.sh
   python harness/sensors/architecture_fitness.py
   bash harness/sensors/run_tests.sh
   ```
2. **Frontend Validation Suite**:
   ```bash
   cd web && pnpm lint
   cd web && pnpm typecheck
   cd web && pnpm test
   bash harness/verify-frontend.sh
   ```

### Manual Verification
1. Open `http://localhost:3000/drift`:
   - Verify that the page loads quickly (< 500ms) with memoized alerts.
   - Click "Show Guide" under "How to read this Manifold" and verify that the accordion expands smoothly, does not disappear, and presents clear KaTeX-compliant formulas.
   - Verify that `DriftManifoldRadar`, `DriftTimelineChart`, and `SeverityAlertsMatrix` render without duplicate empty state graphics.
2. Open `http://localhost:3000/tensor`:
   - Verify that remote tracking branches appear when toggling branch scope.
   - Click any cell in the $\Omega_{ij}$ matrix and verify that the 5-term score breakdown displays correctly with exact weights.
