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
- **Zero-Token-Bleed Inference:**
  - MCP-first: Cursor / Claude Code / Copilot invokes GDSS tools using the client's own model ($0 token cost to GDSS).
  - CI: Uses native GitHub Actions Copilot CLI/Models or user-supplied API secrets.
  - Local: Offline-first; optional Ollama/vLLM without requiring it for core functionality.
- **Two-Brain Purity:** Deterministic engine (`core`, `graph`, `watcher`, `conflict`, `mcp`)
  never depends on the generative AI layer (`ai`). The AI proposes; sandboxed validation tests;
  humans approve. Never auto-merges.

Canonical spec: `PRODUCT_SPEC.md`. Product intent: `docs/PRODUCT_INTENT.md`.
Gap matrix: `docs/IMPLEMENTATION_GAP.md`.
