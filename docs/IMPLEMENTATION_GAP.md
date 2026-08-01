# GDSS Implementation Gap

Status of the product relative to the [North Star](PRODUCT_INTENT.md).  
Machine-readable queue: [`harness/state/feature_list.json`](../harness/state/feature_list.json).  
Do not invent phases here — this matrix mirrors that queue.

## Gap matrix

| Area | Status | Role toward North Star | Gap |
| --- | --- | --- | --- |
| Phase 1 — graph / operators / CLI | done | Structure + transforms | — |
| Phase 2 — embeddings + `/similar` UI (F6 / F6.1) | done | Assistive neighborhood / PCA cloud | Never authoritative for merge risk |
| Phase 3 — drift / alerts | done | Divergence from attractor | Drift CLI Conflict P still flat heuristic |
| F0–F6.1 frontend + local API honesty | done | Visible status / graph / drift / embedding | — |
| **phase4-tensor** | **done** | Flat rank-2 pairwise Ω marginal + commutativity + `gdss tensor` | Geometric Ω deferred to 4a–c |
| phase4a–e geometry | pending | Metric G, transport P, geometric Ω, geodesic, rank-N | Open-ended; see MANIFOLD_TENSOR_GUIDE |
| phase5-ai | pending | Suggest only; never auto-merge | Ready (deps satisfied) |
| phase6-validation | pending | Evidence suggestions pass checks | Blocked on phase5; still not proof |
| **F7 conflict-tensor UI** | **done** | `/tensor` heatmap + `GET /v1/tensor` | similar→Ω deep-link still out of scope |
| phase7-research | pending | Umbrella after 4d+4e | Blocked on geometric phases |
| Line-level semantics as manifold points | out of scope | — | Intentional; not a defect for this goal |

## Ordered missing work (impact on North Star)

1. **`phase5-ai`** — suggestions after deterministic validation hooks; never auto-merge
2. **`phase6-validation`** — evidence of working, not a guarantee
3. **Geometric ladder (4a→4e)** — when researching beyond flat space; not blocking phase5
4. **Small debts** — honor `ref` on `/v1/graph`; wire `/v1/drift/history` into sparklines; optional similar→Ω bridge

## Known honesty rules

- Do not invent dashboard metrics that the backend does not emit
- Embeddings / PCA / similar = assistive only
- Flat Ω ≠ geometric ⟨v_i, P(v_j)⟩_G until phase4c
- Drift `/v1/drift` Conflict P remains flat heuristic; real Ω lives on `/tensor` + `/v1/tensor`

## Next session default

Pick **`phase5-ai`**. Geometry 4a+ only if explicitly pursuing research.
