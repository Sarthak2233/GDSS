# GDSS Implementation Gap

Status of the product relative to the [Master Specification](../PRODUCT_SPEC.md) and [North Star](PRODUCT_INTENT.md).  
Machine-readable queue: [`harness/state/feature_list.json`](../harness/state/feature_list.json).  

## Restructured Product Gap Matrix

| Product Phase | Old ID | Status | Role toward North Star | Gap / Action |
| :--- | :--- | :--- | :--- | :--- |
| **Phase A: Foundation** | Phase 1 & 2 | **done** | AST parser, operators, dependency graph, embeddings | Maintained |
| **Phase B: Collision Radar** | Phase 3 & 4 | **done** | Pairwise collision matrix ($\Omega_{ij}$), commutativity, affected symbols | Maintained |
| **Phase C: Convergence Assistant** | Phase 5 & 6 | **done** | Provider-neutral AI adapter, laser prompts, sandboxed patch validation, guarded apply (`gdss apply`) | Maintained |
| **Phase D: Delivery Interfaces** | New | **done** | MCP server (`gdss mcp`) + GitHub Actions PR audit (`gdss audit-pr`) | Maintained |
| **Phase E: Visual Dashboard UI** | Phase F | **active** | Next.js 14 web UI with collision heatmaps, 3D constellation, and validation evidence | Phase F9 (Validation Sandbox UI) |
| **Phase F: Bespoke IDE Extension** | New | **deferred** | Dedicated VS Code / Copilot extension UI | Deferred until MCP adoption is established |
| **Phase R: Geometric Research** | Phase 4a–4e | **research** | Metric $G$, parallel transport $P$, rank-$N$ octopus on $M^N$ | Frozen on research track; does not block product path |

## Active & Next Focus Areas

1. **`frontend-validation-ui` (Phase F9)** — Surface ephemeral worktree sandbox evidence (tests passed, static types, syntax checks) and guarded apply preflight status in the Next.js visual dashboard.
2. **`sp1-telemetry` & Policy Enforcement** — Hard merge gate controls (`fail_on_collision` based on $\Omega_{ij}$ risk threshold) and explicit telemetry opt-out flags.
3. **`sp1-distribution`** — PyPI packaging and Homebrew release automation.
4. **`Phase R` (Geometry research)** — Explored strictly as an offline research hypothesis, never gating product releases.

## Known Honesty Rules

- MCP tools do not make hidden LLM calls; the calling agent powers the conversation ($0 token bleed).
- Deterministic analysis works 100% offline without any API keys or models.
- Sandboxed validation tests candidate patches in temporary worktrees before showing them to humans; never auto-merges.
- User-facing surfaces use pragmatic terminology (Collision Radar, Merge Order, Affected Symbols), not alienating geometric jargon.
