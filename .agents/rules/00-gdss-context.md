---
description: Core context for what GDSS is and the mission behind it
alwaysApply: true
---

# GDSS Context

GDSS is a **Semantic Branch Intelligence and Merge Assistance Platform** (PR Collision Radar
& Convergence Assistant), built as a semantic intelligence layer above Git.

## Core Identity
- **Pragmatic Developer Tool First:** Product decisions are judged by whether they help
  engineers detect, explain, prioritize, or safely resolve conflicts across concurrent branches.
- **Underlying Intelligence:** Uses deterministic Tree-sitter AST symbol tracking, dependency
  graphs, and commutativity algebra as its mathematical backbone.
- **Deterministic Core + Bring Your Own Key (BYOK) Inference:**
  - Deterministic Core (0 Tokens): AST parsing, dependency graphs, $\Omega_{ij}$ tensor, and merge ordering run on CPU at $0 cost and 0 tokens.
  - MCP-first: Cursor / Claude Code / Copilot invokes local GDSS tools; the developer's IDE subscription powers the chat ($0 tokens to GDSS).
  - CI: Repository admin sets team API secret once in GitHub Secrets (BYOK), or uses native Copilot CLI; deterministic collision radar runs even with zero keys.
  - Local: Offline-first; optional Ollama/vLLM or personal API keys for LLM patch drafting.
- **Two-Brain Purity:** Deterministic engine (`core`, `graph`, `watcher`, `conflict`, `mcp`)
  never depends on the generative AI layer (`ai`). The AI proposes; sandboxed validation tests;
  humans approve. Never auto-merges.

Canonical spec: `PRODUCT_SPEC.md`. Product intent: `docs/PRODUCT_INTENT.md`.
Gap matrix: `docs/IMPLEMENTATION_GAP.md`.
