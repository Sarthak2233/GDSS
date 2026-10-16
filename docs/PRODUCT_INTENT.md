# GDSS Product Intent (North Star)

Master specification: [`PRODUCT_SPEC.md`](../PRODUCT_SPEC.md).  
Canonical statement of **what GDSS is for**. Living queue: [`harness/state/feature_list.json`](../harness/state/feature_list.json). Implementation status: [`IMPLEMENTATION_GAP.md`](IMPLEMENTATION_GAP.md). Vision archive: [`FROM WHERE IT ALL STARTED.md`](../FROM%20WHERE%20IT%20ALL%20STARTED.md).

## Goal

GDSS is a **Semantic Branch Intelligence and Merge Assistance Platform** (PR Collision Radar & Convergence Assistant). It raises the odds of successful collaboration by:

- Detecting **semantic branch collisions** and drift before merge across concurrent PRs
- Naming **affected symbols** (functions, classes, callers, imports)
- Calculating the **branch collision matrix ($\Omega_{ij}$)** and recommending optimal integration order
- Proposing sandboxed, syntax-validated **resolution patches** for human review
- Exposing zero-token-bleed tools via **Model Context Protocol (MCP)** and **GitHub Actions**

It is a **semantic intelligence layer above Git**, not a replacement for Git, CI, or code review.

## Non-goals

- **Not a perfect-code factory.** GDSS does not produce or guarantee “perfect working code.”
- **Not a universal merge oracle.** Program equivalence and halting are undecidable; never claim otherwise.
- **Never auto-merge.** Predict and suggest; humans decide what lands.
- **Never autonomously edit a workspace.** A future local apply operation may change one
	explicitly selected, validated suggestion only after a human confirmation and preflight;
	it must never select a strategy or run Git merge, rebase, stage, commit, push, or pull.
- **Not a line-level IDE merge UI.** Analysis is symbol-centric, not every source line as a manifold point.
- **Not a chatbot / autocomplete** for writing features.

Correctness of shipped code remains **tests, types, review, and humans**. Validation (phase 6) can add *evidence* that a suggestion passes checks — still not a proof of correctness.

## Unit of analysis

| First-class | Role |
| --- | --- |
| Symbols (`function`, `class`, `import`, `variable`, `constant`) | Graph nodes, operators, embeddings, drift affected set |
| Semantic operators (`ADD_*`, `RENAME_*`, `MODIFY_*`, …) | Transforms / tangent steps |
| BodyBlocks / structural tokens | Support `MODIFY_*` detection inside a symbol — **not** first-class UI/graph nodes |

Ignoring “every line of code” as a first-class object is **intentional** for this goal, not a defect.

## Two-brain honesty

- **Deterministic brain** (`core`, `graph`, `watcher`, later `conflict`): trusted structure, operators, commutativity / \(\Omega_{ij}\).
- **Assistive brain** (`embeddings`, later `ai`): probabilistic neighbors and suggestions — always labeled assistive; never authoritative for merge risk alone.

## Success metric

Earlier, more accurate **merge-risk / drift signal**, plus **human-controlled** suggestions when AI lands — **not** “100% green builds” or “perfect merges.”

## Agentic workflow boundary

An optional agent orchestrator may coordinate deterministic analysis, an opted-in local model,
validation, and human review checkpoints. It is not a decision-maker: deterministic GDSS modules
remain the source of ranking, topology, and validation evidence. The orchestrator is review-only
until the later human-approved apply phase, and all persisted or API-visible run state is
metadata-only.

## Related

- Operating manual: [`AGENTS.md`](../AGENTS.md)
- Gap matrix: [`IMPLEMENTATION_GAP.md`](IMPLEMENTATION_GAP.md)
- Frontend roadmap: [`FRONTEND_ROADMAP.md`](FRONTEND_ROADMAP.md)
