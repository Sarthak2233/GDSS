---
name: Phase4 flat tensor + geometric phases
overview: "Reframe phase4 as the flat rank-2 Ω (NOW), and add dedicated open-ended phases to feature_list.json for the missing geometric pieces: Riemannian metric, parallel transport, geometric Ω, geodesic optimum plane, and the rank-N M^N generalization."
todos:
  - id: now-implement-flat-tensor
    content: "Implement phase4-tensor NOW: commutativity.py + tensor.py + gdss tensor CLI (TDD, 5 slices)"
    status: pending
  - id: refine-phase4-criteria
    content: Refine phase4-tensor done_criteria in feature_list.json to 'flat rank-2 pairwise marginal'
    status: pending
  - id: add-phase4a-metric
    content: Add phase4a-riemannian-metric to feature_list.json (open-ended)
    status: pending
  - id: add-phase4b-transport
    content: Add phase4b-parallel-transport to feature_list.json (open-ended)
    status: pending
  - id: add-phase4c-geom-tensor
    content: Add phase4c-geometric-tensor to feature_list.json (open-ended)
    status: pending
  - id: add-phase4d-geodesic
    content: Add phase4d-geodesic-merge to feature_list.json (open-ended)
    status: pending
  - id: add-phase4e-rankN
    content: Add phase4e-config-tensor (rank-N on M^N) to feature_list.json (open-ended)
    status: pending
  - id: update-phase7-research
    content: Update phase7-research deps to umbrella the new geometric phases
    status: pending
  - id: verify-and-state
    content: verify.sh green; mark phase4-tensor done; update progress.md + session-handoff.md
    status: pending
isProject: false
---

# Phase 4 — Flat Conflict Tensor (NOW) + Geometric Phases (LATER)

## What this plan does

1. Reframes `phase4-tensor` as the **flat rank-2 Ω** — the pairwise marginal, implemented now.
2. Adds **5 new dedicated phases** to `harness/state/feature_list.json` for the missing geometric concepts from `docs/MANIFOLD_TENSOR_GUIDE.md`, with open-ended done_criteria.
3. Updates `phase7-research` to umbrella the new geometric phases.

## Why rank-2 now (the math, settled)

- `Ω_{ij}` is rank-2 because **merges are pairwise**. `R_merge = Σ_{i,j} Ω_{ij}`.
- The manifold `M` (program-state space) is **fixed** — branches are trajectories on it, not dimensions.
- The rank-N tensor on `M^N` (the user's intuition) is the **N-way simultaneous** object; rank-2 is its pairwise marginal. Build the marginal first (feasible, `N²`), defer the full rank-N object (exponential, mostly redundant).

## Part A — Implement NOW: phase4-tensor (flat rank-2 Ω)

Same 5 TDD slices already in the plan file, unchanged in substance, just reframed as "the flat-space limit":

1. `gdss/conflict/commutativity.py` — `CommutativityClass` enum, `classify(a,b)`, `commutativity_table()`, `operator_interference(sets) -> (interfering, contact)`.
2. `gdss/conflict/tensor.py` — `TensorEntry`, `ConflictTensor`, `TensorEngine.compute(branch_ops, drift_magnitudes, impact_sets)`; sparse dict-of-dicts; `Ω_{ii}` = drift diagonal; `R_merge = Σ Ω`.
3. CLI `gdss tensor` + `do_tensor` (Rich N×N matrix) in `gdss/cli/main.py` and `gdss/cli/start.py`.
4. Tests: `tests/conflict/test_commutativity.py`, `test_tensor.py`, `tests/cli/test_tensor_cli.py`.
5. `bash harness/verify.sh` green; mark `phase4-tensor` done; update `progress.md` + `session-handoff.md`.

Architecture: conflict (L7) must NOT import drift (L8) or embeddings (L6) — drift magnitudes passed in by caller. Enforced by `tests/conflict/test_conflict_architecture.py`.

## Part B — Add to feature_list.json (LATER, open-ended)

Insert these 5 phases after `phase4-tensor` (line 122). All `layer: "geometry"`, all `status: "pending"`, open-ended criteria.

- **phase4a-riemannian-metric** (1.4a): Riemannian metric `G` on `M` as pullback from embeddings `φ: M → R^m`, `G_C(u,v) = (Dφ_C u)^T (Dφ_C v)`. Replaces flat cosine. deps: `phase4-tensor`.
- **phase4b-parallel-transport** (1.4b): `P_{j→i}` semantic rebase — re-extract branch j's operators on top of branch i's tip via sandbox. deps: `phase4a-riemannian-metric`.
- **phase4c-geometric-tensor** (1.4c): `Ω_{ij} = ⟨v_i, P_{j→i}(v_j)⟩_G`. deps: `phase4a`, `phase4b`.
- **phase4d-geodesic-merge** (1.4d): optimum merge plane — minimize `R_merge` over merge orders (Hopf-Rinow existence; sandbox search). deps: `phase4c-geometric-tensor`.
- **phase4e-config-tensor** (1.4e): rank-N tensor on `M^N` for N-way/octopus merges; rank-2 is its marginal. Open research. deps: `phase4c-geometric-tensor`.

Update **phase7-research** (line 146): change deps to `[phase4d-geodesic-merge, phase4e-config-tensor]` and note it umbrellas experimental refinements.

## Part C — Refine phase4-tensor done_criteria

Change line 121 from `"gdss/conflict/* computes Omega_{ij} + commutativity table; tests green"` to:

`"Flat rank-2 conflict tensor: gdss/conflict/{commutativity,tensor}.py compute sparse Omega_{ij} (pairwise marginal, vision-doc weights) + commutativity table + R_merge; no gdss.drift import; gdss tensor CLI; tests + verify.sh green. Geometric form (metric G, transport P, <v_i,P(v_j)>_G) deferred to phase4a-d."`

## Out of scope for the NOW slice

- No metric, no transport, no geodesic, no rank-N. Those are the new phases.
- No daemon `"conflict"` event, no frontend viz.

## Success evidence

- `phase4-tensor` done (flat Ω matrix + R_merge + commutativity table), verify.sh green.
- 5 new open-ended phases registered in feature_list.json with correct deps.
- `docs/MANIFOLD_TENSOR_GUIDE.md` referenced as the math source for the geometric phases.