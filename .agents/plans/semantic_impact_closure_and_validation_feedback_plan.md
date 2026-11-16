# Implementation Plan: Semantic Change-Impact Closure and Validation Feedback Architecture

This plan establishes repository-level semantic consistency during automated merge assistance. It implements the three-engine architecture to eradicate the vulnerability where **local conflict resolution myopically masquerades as global repository correctness**.

---

## Goal Description

When concurrent branches introduce conflicting AST mutations or interface changes, reconciling the conflict site alone is rarely sufficient. A single function renaming or signature adaptation induces ripples across downstream callers, schema contracts, and test suites.

This change delivers an end-to-end deterministic and probabilistic system:
1. **Engine 1: Deterministic Semantic Impact Closure (SIC) Engine (`gdss/graph/impact_closure.py`)**:
   Computes the transitive 2-hop impact envelope ($S^*$) expanding conflict symbols ($C_0$) across callers, contract interfaces, and verifying test suites ($T(C_0)$) at $0 token cost.
2. **Engine 2: Multi-File Coordinated Patch Packaging & Synthesis (`gdss/ai/context_builder.py`, `gdss/validation/guarded_apply.py`)**:
   Synthesizes unified multi-file git diffs spanning the conflict site and all downstream callers with proportional token budgeting (50% / 30% / 20%), backed by all-or-nothing atomic rollback.
3. **Engine 3: Closed-Loop Validation Diagnostics & Anti-Gaming Invariants (`gdss/validation/diagnostic_extractor.py`, `gdss/validation/sandbox.py`, `gdss/ai/orchestration.py`)**:
   Performs pre-flight differential baseline runs in ephemeral worktrees, extracts structured failure diagnostics ($E_k$), prevents test assertion degradation (Goodhart's Law), and feeds structured diagnostics back into iterative patch refinement.

Formal Problem Specification: [`docs/problem-definations/Semantic Change-Impact Closure and Validation Feedback Problem.md`](file:///home/sarakb/projects/GDSS/docs/problem-definations/Semantic%20Change-Impact%20Closure%20and%20Validation%20Feedback%20Problem.md)  
Formal Solution Specification: [`docs/problem-definations/solutions/Semantic Change-Impact Closure and Validation Feedback Solution.md`](file:///home/sarakb/projects/GDSS/docs/problem-definations/solutions/Semantic%20Change-Impact%20Closure%20and%20Validation%20Feedback%20Solution.md)

---

## User Review Required

> [!IMPORTANT]
> **Deterministic Core Purity (0 Tokens)**  
> Engine 1 (SIC graph traversal), Pre-Flight Baseline Test Execution, and Diagnostic Extraction ($E_k$) run 100% locally on CPU without requiring an LLM or consuming tokens. LLM inference is strictly isolated to candidate code synthesis in `gdss/ai/`.

> [!WARNING]
> **Anti-Gaming Invariant Policy on Tests**  
> 1. The convergence assistant **is** permitted to adapt test function call signatures, update symbol imports, and add new test cases when an API signature legitimately changes.  
> 2. The convergence assistant is **strictly quarantined** from deleting or weakening test assertions (`assert x == y`). Any modified assertion triggers an `ANTI_GAMING_WARNING` and isolates the test diff for mandatory human approval.

---

## Open Questions

None. All architectural decisions (3-engine phased sequence, 2-hop weighted expansion, atomic git diff format, anti-gaming test policy, pre-flight differential baseline, and proportional symbol slicing) were resolved during Rounds 1 and 2 of the design interview.

---

## Proposed Changes

```mermaid
graph TD
    subgraph Layer 1: Deterministic Core (0 Tokens, CPU)
        AST["ASTParser"] --> CG["CodeGraph"]
        CG --> SIC["[NEW] gdss/graph/impact_closure.py<br/><i>Computes S* & maps T(C0)</i>"]
        WT["Ephemeral Worktree"] --> BASE["Pre-Flight Baseline (F_base)"]
        WT --> CAND["Candidate Validation"]
        CAND --> DIAG["[NEW] gdss/validation/diagnostic_extractor.py<br/><i>Extracts Ek & enforces anti-gaming</i>"]
    end

    subgraph Layer 2: Probabilistic Brain (BYOK / LLM)
        CTX["[MODIFY] gdss/ai/context_builder.py<br/><i>AST Symbol Slicing & Budgeting</i>"]
        ORCH["[MODIFY] gdss/ai/orchestration.py<br/><i>Iterative Feedback with Ek</i>"]
    end

    subgraph Layer 3: Guarded Local Apply
        APPLY["[MODIFY] gdss/validation/guarded_apply.py<br/><i>Atomic Multi-File Rollback</i>"]
    end

    SIC --> CTX
    CTX --> ORCH
    DIAG -->|Ek Diagnostics| ORCH
    ORCH --> APPLY
```

---

### Component 1: Engine 1 — Deterministic Semantic Impact Closure (SIC)

#### [NEW] `gdss/graph/impact_closure.py`
- Implements `compute_semantic_impact_closure(code_graph, conflict_symbols, max_hops=2, relevance_threshold=0.70, token_budget=4000) -> ImpactClosureResult`.
- Traverses 2 hops in the reverse dependency graph ($G_{\text{rev}}$) using weighted edge traversal ($O(|V| + |E|)$).
- Weights: Direct call (1.00), Type annotation / inheritance (0.95), Test coverage (0.90), Import (0.50), Lexical (0.25).
- Identifies verifying test suites $T(C_0)$ using test pattern discovery, file conventions, and AST import graphs.
- Budget-aware pruning: if estimated tokens exceed `token_budget`, preserves $C_0$, direct callers, and tests, shedding low-confidence 2-hop edges ($w < 0.80$).

```python
# gdss/graph/impact_closure.py
@dataclass(frozen=True)
class ClosureNode:
    symbol_id: str
    file_path: str
    node_type: str  # "function", "class", "contract", "test"
    hop_distance: int
    weight: float
    implicated_by: str

@dataclass(frozen=True)
class ImpactClosureResult:
    conflict_symbols: tuple[str, ...]
    closure_nodes: tuple[ClosureNode, ...]
    implicated_files: tuple[str, ...]
    target_tests: tuple[str, ...]
    contract_files: tuple[str, ...]
    total_estimated_tokens: int
```

---

### Component 2: Engine 2 — Multi-File Coordinated Patch Packaging & Synthesis

#### [MODIFY] `gdss/ai/context_builder.py`
- Extends `SemanticCollisionContext` to include `impact_closure: ImpactClosureResult`.
- Implements AST symbol slicing: extracts only target functions, signatures, and call sites from caller files, instead of dumping entire monolithic files.
- Implements proportional token budgeting:
  - 50% budget to 3-way conflict code ($C_0$).
  - 30% budget to direct callers and contracts ($D(C_0) \cup K(C_0)$).
  - 20% budget to verifying tests and diagnostic traces ($T(C_0) \cup E_k$).

#### [MODIFY] `gdss/validation/guarded_apply.py`
- Extends `apply_unified_diff` to parse and apply standard multi-file git diffs (`diff --git a/... b/...`, `--- a/...`, `+++ b/...`).
- Extends `apply_suggestion` to execute all-or-nothing atomic rollback:
  - Backs up all target files into `.gdss/rollback/{suggestion_id}.json`.
  - Writes new contents to all target files.
  - Runs post-apply AST syntax validation on **all** modified files.
  - If *any* file fails syntax validation, restores all files to original content immediately.

---

### Component 3: Engine 3 — Closed-Loop Validation Diagnostics & Anti-Gaming Invariants

#### [NEW] `gdss/validation/diagnostic_extractor.py`
- Implements structured diagnostic parsing from raw tool output:
  - `parse_test_diagnostics(tool_name: str, raw_output: str, exit_code: int) -> DiagnosticPayload`
  - Extracts failure type (`AssertionError`, `TypeError`, `SyntaxError`), expected vs. actual values, line numbers, tracebacks, and implicated symbols.
- Implements differential baseline comparison:
  - `compute_differential_diagnostics(candidate_diag, baseline_diag) -> DiagnosticPayload`
  - Isolates true regressions ($\Delta F_k = F_{\text{candidate}} \setminus F_{\text{base}}$) tagged `INTRODUCED_BY_PATCH`.
  - Tags $f \in F_{\text{base}}$ as `PRE_EXISTING_BASELINE` (suppressed from penalizing the patch).
- Implements AST test anti-gaming invariant checker:
  - `inspect_test_diff_anti_gaming(original_content: str, patched_content: str) -> AntiGamingCheckResult`
  - Inspects AST nodes for deleted or weakened assertion statements (`assert`, `self.assert*`, `expect(...)`).
  - Emits `ANTI_GAMING_WARNING` if assertions were modified or deleted.

#### [MODIFY] `gdss/validation/sandbox.py`
- Adds pre-flight baseline execution `_run_baseline_validation()`:
  - Executes targeted tests on clean worktree $R_0$ before applying patch.
  - Caches baseline results by commit SHA.
- Attaches structured `DiagnosticPayload` to `ValidationReport`.

#### [MODIFY] `gdss/ai/orchestration.py`
- Updates `validate_step` to record structured diagnostics on rejected combinations.
- Updates `refine_step` to feed structured $E_k$ payload into `build_refinement_prompt`.
- Enforces anti-gaming quarantine: suggestions with `ANTI_GAMING_WARNING` are flagged as requiring explicit human confirmation.

---

### Component 4: Test Suites & Verification Sensors

#### [NEW] `tests/graph/test_impact_closure.py`
- Unit tests for `compute_semantic_impact_closure`:
  - 1-hop direct callers and type annotations.
  - 2-hop transitive callers with weight filtering ($\theta = 0.70$).
  - Token budget pruning.
  - Mapping verifying test files.

#### [NEW] `tests/validation/test_diagnostic_extractor.py`
- Unit tests for `parse_test_diagnostics`:
  - Parsing pytest, vitest, and cargo test outputs.
  - Traceback and assertion extraction.
  - Differential baseline subtraction ($F_{\text{candidate}} \setminus F_{\text{base}}$).

#### [NEW] `tests/validation/test_anti_gaming.py`
- Unit tests for `inspect_test_diff_anti_gaming`:
  - Call signature updates in tests pass cleanly.
  - Assertion deletion or threshold relaxing triggers `ANTI_GAMING_WARNING`.

#### [NEW] `tests/ai/test_multi_file_patch.py`
- Integration tests for multi-file patch synthesis:
  - Context building with proportional budgeting and AST symbol slicing.
  - Atomic application and automatic rollback in `guarded_apply.py`.

---

## Verification Plan

### Automated Tests
Execute the full GDSS verification gate across all layers:

```bash
# 1. Run new unit and integration test suites
pytest tests/graph/test_impact_closure.py -v
pytest tests/validation/test_diagnostic_extractor.py -v
pytest tests/validation/test_anti_gaming.py -v
pytest tests/ai/test_multi_file_patch.py -v

# 2. Run Layer 1 Static & Two-Brain Purity Sensors
bash harness/sensors/lint.sh
bash harness/sensors/typecheck.sh
python harness/sensors/architecture_fitness.py

# 3. Run full verification gate (Layer 1 + Layer 2 + Layer 3)
bash harness/verify.sh
```

### Manual Verification
1. Run CLI smoke test on a multi-file conflict fixture:
   ```bash
   gdss analyze --repo tests/fixtures/sample_repo
   gdss suggest --repo tests/fixtures/sample_repo --validate
   ```
2. Verify that `ImpactClosureResult` and structured diagnostics appear in the JSON suggestion metadata under `.gdss/suggestions/`.
3. Verify that `gdss apply` successfully applies a multi-file patch atomically, and rolls back all files if syntax validation fails on any file.

