# 🎯 GDSS AI Prompt Engineering & Unified Context Architecture Plan

> **A Rigid Architectural Plan to Transform GDSS Prompt Engineering, 3-Way Semantic Context Assembly, and Tool-Aware Agentic Convergence into a Production-Worthy, Single-Source-of-Truth Engine.**

---

## 📑 Executive Summary & Diagnostic Findings

GDSS is designed to be an **Air Traffic Control Radar & Convergence Assistant** above Git: deterministic at the core, with AI synthesis powered by high-precision prompts and sandboxed validation. 

However, an exhaustive audit of the AI and prompt engineering subsystem across `gdss/ai/`, `gdss/validation/`, `gdss/cli/`, and `gdss/drift/` reveals **six critical architectural flaws**:

```
Current Fragmented Architecture:
┌──────────────────┐     ┌──────────────────────────────────┐     ┌────────────────────────────────┐
│ CLI suggest      ├────►│ build_analysis_context           ├────►│ suggester.py                   │
│ (--as-prompt)    │     │ (branch_intents EMPTY)           │     │ (anchored_block: 1 branch only)│
└──────────────────┘     └──────────────────────────────────┘     └───────────────┬────────────────┘
                                                                                  │
┌──────────────────┐     ┌──────────────────────────────────┐                     ▼
│ CI audit-pr      ├────►│ build_pr_analysis_context        │       build_conflict_prompt()
│ (LangGraph state)│     │ (has PR intents & commits)       │       (Dead/vague instructions;
└─────────┬────────┘     └──────────────────────────────────┘        no unified diff grammar)
          │
          │ Fallback (line 659)
          ▼
┌───────────────────────────────────────────────────────────┐
│ generate_pr_convergence_patch() [pr_audit.py:358]         │
│ - Ad-hoc hardcoded string prompt                          │
│ - ZERO source code provided to model!                     │
│ - ZERO context window budgeting (condensation bypassed)   │
│ - Bypasses prompt_builder.py and orchestration.py         │
└───────────────────────────────────────────────────────────┘
```

---

## 🔍 The 6 Core Problems Diagnosed

### 1. Incomplete 3-Way Semantic Context (The "One-Branch Blind Spot")
- **What happens:** In `gdss/ai/suggester.py:70`, `_anchored_block()` extracts lines strictly from `anchor.target_branch`.
- **The flaw:** When Branch A and Branch B collide on symbol `login()`:
  - Branch A modified `login()` (e.g., added OAuth tokens).
  - Branch B modified `login()` (e.g., added timeout parameter).
  - Base (`reference_branch`) had the original definition.
  - The model is only shown Branch A's code block! For Branch B, the prompt only provides the operator name string (e.g., `"Branch B applies modify_function to login"`).
- **Impact:** The LLM has to hallucinate what Branch B's implementation looks like. It frequently drops Branch B's parameters or logic, resulting in sandboxed validation failures.

### 2. Standalone, Disconnected Prompt Stubs in CI (`pr_audit.py`)
- **What happens:** In `gdss/validation/pr_audit.py:358-415`, `generate_pr_convergence_patch()` defines an ad-hoc inline string prompt:
  ```python
  prompt = (
      f"You are an automated merge conflict convergence assistant in GitHub Actions CI.\n"
      f"Target File: {target_file}\n"
      f"Colliding Symbol: {overlapping_symbol}\n"
      f"Incoming PR changes: {cur_desc or 'modified definition'}\n"
      f"Concurrent PR changes: {oth_desc or 'modified definition'}\n"
      ...
  )
  ```
- **The flaw:** It passes **zero code** to the model—only human-readable operator names. It bypasses `prompt_builder.py`, `condensation.py`, and `orchestration.py`.
- **Impact:** Any PR audit falling into this path requests code synthesis without code, producing instant hallucinations and syntax errors.

### 3. Dead and Ineffective Functions in `prompt_builder.py`
- **What happens:** 
  - `build_prompt()` (lines 92-100) is a dead function never called by production code (only in an obsolete unit test). It outputs a list of `_suggestion_lines()` with no code blocks or line ranges.
  - `build_conflict_prompt()` appends `"DO NOT apply or run anything; return only patch text with file paths and line ranges."` without providing a grammar, schema, or example of what the patch should look like.
- **The flaw:** The model does not know whether to produce a Unified Diff, a replacement function, or JSON.

### 4. Severe Output Grammar & Validation Mismatch
- **What happens:**
  - `gdss/ai/validation.py:validate_patch()` strictly requires a Unified Diff (`--- a/...`, `+++ b/...`, `@@ -start,count +start,count @@`).
  - `gdss/ai/patch_parser.py:parse_strategy_patches()` requires custom multi-strategy headers (`--- patch: ... (strategy: ...) ---`).
  - `gdss/validation/pr_audit.py` asks the model for a clean replacement function block (`Output ONLY the reconciled code block to replace '{overlapping_symbol}'`).
  - `gdss/ai/prompt_builder.py:build_refinement_prompt()` says: `"Output ONLY the corrected replacement code block or patch."`
- **Impact:** The model outputs a clean replacement block (e.g. `def login(): ...`), which `validate_patch` immediately rejects with `"patch must contain exactly one file"`, triggering unnecessary refinement loops or total failure.

### 5. Context Split Between CLI and CI
- **What happens:**
  - `build_analysis_context()` (`drift/context.py`) leaves `branch_intents` empty (`{}`).
  - `build_pr_analysis_context()` (`drift/context.py`) populates `branch_intents`, but builds a custom tracked branch list.
  - CLI `gdss suggest --as-prompt` duplicates block extraction in `main.py:282-287`.
  - REST API `/v1/suggest?format=prompt` does not return prompts at all—it returns raw metadata dictionaries.
- **Impact:** Context assembly is fragmented across 4 different callers with diverging fidelity.

### 6. Missing Tool Access Guidance & System Prompt Architecture
- **What happens:** All providers (`OpenAICompatibleProvider`, `OllamaProvider`) send prompts as a single flat `user` message.
- **The flaw:** The AI receives no `system` prompt establishing its persona as a deterministic compiler and AST reconciler. Furthermore, in IDE/MCP environments, the prompt does not inform the assistant about the deterministic tools it has available (`gdss_find_collisions`, `gdss_inspect_symbol_impact`, `gdss_validate_patch`, `gdss_sandbox_validate_patch`).

---

## 🏗️ The Target Architecture: Unified Single-Source-of-Truth

```
                        ┌──────────────────────────────────────────────┐
                        │          Unified AnalysisContext             │
                        │  (Base ref, Branch A, Branch B, AST Trees,   │
                        │   Commits, PR Intents, Call/Import Graphs)   │
                        └──────────────────────┬───────────────────────┘
                                               │
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │         gdss.ai.context_builder              │
                        │  Extracts 3-Way Semantic Representation:     │
                        │  - V_base: AST symbol at reference_branch    │
                        │  - V_A:    AST symbol at branch_a            │
                        │  - V_B:    AST symbol at branch_b            │
                        │  - Callers: Upstream/downstream blast radius │
                        │  - Budget: condensation.py context window    │
                        └──────────────────────┬───────────────────────┘
                                               │
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │         gdss.ai.prompt_builder               │
                        │  (Single Source of Truth for Prompt Engine)  │
                        │                                              │
                        │  1. System Prompt (Persona, Zero-Hallucination)│
                        │  2. 3-Way Code Inspection Blocks             │
                        │  3. Upstream Impacted Callers Graph          │
                        │  4. Topology Operational Rules               │
                        │  5. Strict Output Grammar & Delimiter Schema │
                        │  6. Tool Capabilities Notice (MCP / IDE)     │
                        └──────────────────────┬───────────────────────┘
                                               │
                     ┌─────────────────────────┼─────────────────────────┐
                     ▼                         ▼                         ▼
              Mode 1 & 2 (CLI/MCP)       Mode 3 (CI Radar)        Mode 4 (REST API)
              gdss suggest / mcp        gdss audit-pr             /v1/suggest?format=prompt
              --as-prompt / --llm       (orchestration.py)        (Consistent prompt JSON)
```

---

## 📋 Comprehensive Implementation Roadmap

### Phase 1: 3-Way Semantic Symbol Extraction (`gdss/ai/context_builder.py`)
Extract the complete semantic triangle before constructing any prompt:
1. **Base Definition ($V_{base}$)**: The canonical symbol implementation on the `reference_branch`.
2. **Branch A Definition ($V_A$)**: The implementation on the candidate/incoming branch.
3. **Branch B Definition ($V_B$)**: The implementation on the concurrent/other branch.
4. **Callers & Contract Surface**: List of functions and files calling this symbol in Branch A and Branch B (retrieved from `CodeGraph` and `TransformExtractor`).
5. **Context Window Condensation**: If $V_{base} + V_A + V_B + \text{Callers}$ exceeds the model's code budget (`condensation.get_model_code_budget`), use AST-aware pruning to condense unmodified helper functions while preserving signatures and contract touchpoints.

### Phase 2: Complete Overhaul of `gdss/ai/prompt_builder.py`
Transform `prompt_builder.py` into a production-grade prompt engineering engine:
1. **Remove Dead Functions**: Deprecate and remove obsolete `build_prompt()`.
2. **System Prompt Architecture**:
   - Define `SYSTEM_CONVERGENCE_PROMPT`: Establish role as *Principal Software Integration Engineer & AST Semantic Reconciler*.
   - Zero-hallucination rules: Preserve unchanged logic, honor parameter typing contracts, maintain strict syntax validity for the target programming language.
3. **Topology-Specific Operational Directives**:
   - `signature_divergence`: Union parameters with backward-compatible defaults, preserve type annotations.
   - `body_divergence`: Reconcile independent business logic statements inside function bodies.
   - `contract_addition`: Combine newly introduced methods/fields cleanly without shadowing existing declarations.
   - `deletion_conflict`: Check if caller references exist before deleting; provide adapter stub if necessary.
4. **Output Format Modes**:
   - **Mode A: Strict Unified Diff** (`UNIFIED_DIFF`): Complete with `--- a/<path>`, `+++ b/<path>`, `@@ -<start>,<len> +<start>,<len> @@`. Includes few-shot example.
   - **Mode B: Exact Replacement Block** (`REPLACEMENT_BLOCK`): Complete with standard markdown fence tagged with language (e.g. ````python ... ````) and symbol markers.
5. **Refinement Prompt Overhaul (`build_refinement_prompt`)**:
   - Structured sections: Previous Attempt, Compiler/Linter Error Trace, Failed Verification Gate (Syntax, Typecheck, or Tests), and Clear Fix Objectives.
6. **Tool-Aware Prompt Addendum (`build_tool_aware_prompt`)**:
   - When generating prompts for IDE agents or MCP clients, append a section detailing available deterministic GDSS tools (`gdss_validate_patch`, `gdss_inspect_symbol_impact`, `gdss_sandbox_validate_patch`).

### Phase 3: Unify Context Assembly Across All Modes
Eliminate divergence between CLI and CI:
1. **Unify `AnalysisContext`**:
   - In `gdss/drift/context.py`, update `build_analysis_context` to scan for Git commit intents and PR descriptions (when available via Git config or local commit messages) so `branch_intents` is consistently populated.
   - Ensure `build_pr_analysis_context` and `build_analysis_context` share the identical 3-way symbol resolution logic.
2. **Remove Ad-Hoc Prompt in `pr_audit.py`**:
   - Delete `generate_pr_convergence_patch()` and `_format_ops_description()`.
   - Route all CI synthesis directly through `ConvergenceState` and `run_convergence_pipeline()`.
   - In the CI fallback path (when no pairwise suggestions were produced by the top-level state machine), construct a properly anchored `Suggestion` and pass it to the unified prompt builder.
3. **Unify CLI `--as-prompt`**:
   - Update `gdss/cli/main.py:suggest` to call the unified `build_conflict_prompt` using the complete 3-way symbol context, eliminating redundant line slicing.
4. **Unify REST API `/v1/suggest`**:
   - In `gdss/api/service.py:get_suggestions`, when `format == "prompt"`, return the full, structured prompt string produced by `build_conflict_prompt()`.

### Phase 4: Output Parsing & Multi-Format Validation Bridge
Bridge the gap between model outputs and validation gates:
1. **Flexible Patch Parser (`gdss/ai/patch_parser.py`)**:
   - Accept either a valid Unified Diff or a fenced Replacement Code Block.
   - If a Replacement Code Block is returned, provide an automatic converter to a unified diff based on the target symbol's anchor boundaries (`SuggestionAnchor`), enabling seamless execution through `ValidationSandbox` and `gdss apply`.
2. **Validation Compatibility (`gdss/ai/validation.py`)**:
   - Support validating both unified diffs and replacement blocks against AST syntax.

### Phase 5: Verification & Fitness Gate
1. **Unit Test Suite**:
   - `tests/ai/test_prompt_builder.py`: Test 3-way symbol injection, system prompt generation, topology rules, output format schemas, and tool access notices.
   - `tests/ai/test_3way_symbol_extraction.py`: Verify that Base, Branch A, and Branch B symbol definitions are extracted accurately across languages (Python, TS, Go).
   - `tests/validation/test_pr_audit.py`: Verify that CI PR collision audit uses the unified prompt pipeline without ad-hoc stubs.
   - `tests/cli/test_suggest_validation_cli.py`: Verify `gdss suggest --as-prompt` outputs complete 3-way context.
2. **Harness Verification**:
   - Execute `bash harness/verify.sh` (must be 100% green: ruff, mypy, architecture fitness, dsa fitness, pytest, cli smoke, and frontend gate).

---

## 🔒 Invariants & Guarantees

1. **Two-Brain Purity**: All prompt construction in `gdss/ai/` remains within the probabilistic brain. It queries deterministic inputs (`AnalysisContext`, `GitObserver`, `ASTParser`) but deterministic modules (`core`, `graph`, `drift`, `watcher`) never import `prompt_builder`.
2. **Zero Token Bleed**: Local deterministic operations (finding collisions, ranking, calculating $\Omega_{ij}$) continue to cost $0 tokens. Prompts are constructed in memory with $0 API fees.
3. **No Code Omission**: An LLM is **never** asked to reconcile a collision without being provided the source code of both branches and the base reference.
4. **Strict Delimiter Schema**: Prompts always use explicit untrusted data fences (`--- UNTRUSTED SOURCE CONTENT BEGIN ---`) to prevent prompt injection from malicious commit messages or source code.
5. **Never Auto-Merge**: The output remains suggestions and patches; humans always approve.

---

## 🚦 Decision Checkpoints & User Approval

Before initiating code modifications, please confirm:
1. Do you approve retiring the dead `build_prompt()` and ad-hoc `generate_pr_convergence_patch()` in favor of the unified 3-way semantic prompt engine?
2. Should the unified prompt support both **Unified Diff** (default for sandbox/apply) and **Clean Replacement Block** (with automatic diff synthesis) formats?
