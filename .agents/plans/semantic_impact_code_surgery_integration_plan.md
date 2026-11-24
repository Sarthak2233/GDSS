# Semantic Impact Closure & Complementary Code Surgery Integration Test Plan

## Goal Description
During our architectural discussion, we identified a critical semantic problem:
When a merge collision occurs in a source file (e.g., `src/auth.py`), reconciling that collision often requires a **complementary patch in a downstream file (e.g., `tests/test_auth.py`)** that was **never touched by either branch and has zero Git diff hunks**. In that downstream file, there may be dozens of test cases and hundreds of lines of code.

This plan details the design and implementation of a dedicated end-to-end integration test suite (`tests/integration/test_semantic_impact_code_surgery.py`) and supporting test cases across the project to verify how GDSS:
1. **Pinpoints the exact caller block**: Tree-sitter and `CodeGraph` isolate the exact test function (`test_login_valid`) calling the collided symbol, while discarding unrelated tests (`test_logout`, `test_oauth`).
2. **Extracts dynamic diagnostic traces ($E_k$)**: Running the candidate patch in an ephemeral sandbox worktree captures the stack trace, failing line number, and exception type.
3. **Synthesizes a multi-file unified diff**: The refinement loop consumes $E_k$ and generates a complementary patch spanning both the collision file and the untouched test file.
4. **Enforces the Anti-Gaming Invariant Sensor**: Ensures that test adjustments adapt parameters rather than "cheating" by deleting or trivializing assertions.
5. **Applies and re-validates atomically**: Applies the multi-file patch atomically via `guarded_apply` and proves that the targeted test suite passes 100% green.
6. **Exposes complete closed-loop parity over IDE MCP**: Verifies that Cursor, Claude Code, and Copilot can execute this entire flow via native MCP tools.

---

## User Review Required

> [!IMPORTANT]
> **Zero Token Invariant & Determinism**: All integration tests will execute 100% offline using real Tree-sitter parsers, real Git worktrees, real pytest runner execution, and mock LLM provider fixtures. No external network requests or API keys will be required.

> [!NOTE]
> **Directory Addition**: We will introduce `tests/integration/` as a dedicated integration test directory. This directory will be automatically discovered by pytest and verified under `bash harness/verify.sh`.

---

## Proposed Changes

### Integration Test Suite

#### [NEW] `tests/integration/test_semantic_impact_code_surgery.py`
A comprehensive, end-to-end integration test suite covering the full closed-loop lifecycle:

```mermaid
sequenceDiagram
    autonumber
    participant Git as Git Repo (Worktree)
    participant SIC as Semantic Impact Closure
    participant Sandbox as Ephemeral Sandbox
    participant Diag as Diagnostic Extractor (E_k)
    participant Loop as Agentic Refinement Loop
    participant AG as Anti-Gaming Sensor
    participant Apply as Guarded Apply

    Git->>SIC: Collision in auth.py::login (untouched tests/test_auth.py)
    SIC->>SIC: AST reverse call-graph pins test_login_valid (L45-L62)
    SIC->>Sandbox: Apply candidate patch for auth.py
    Sandbox->>Sandbox: Execute pytest tests/test_auth.py
    Sandbox->>Diag: Captured failure output
    Diag->>Diag: Extract E_k (tests/test_auth.py:54, TypeError missing tenant_id)
    Diag->>Loop: Feed E_k + AST block (L45-L62)
    Loop->>Loop: Synthesize multi-file diff (auth.py + test_auth.py:54)
    Loop->>AG: Audit test diff
    AG->>AG: Assert count >= original, no trivial assertions
    AG->>Apply: Apply multi-file diff atomically
    Apply->>Sandbox: Re-run pytest in worktree
    Sandbox-->>Apply: 100% PASSED (0 errors)
```

The test file will implement the following 6 test scenarios:

1. `test_ast_callsite_pinpointing_in_untouched_test_file`:
   - Builds a real test file with multiple tests (`test_logout`, `test_login_valid`, `test_oauth`).
   - Verifies that `CodeGraph` and `compute_semantic_impact_closure` flag `test_login_valid` as Hop 1 and accurately isolate lines 45–62, while `test_logout` and `test_oauth` have 0 edges.

2. `test_sandbox_diagnostic_trace_pinpointing_ek`:
   - Sets up a real temporary Git repository.
   - Applies a signature-changing patch to `auth.py`.
   - Runs `SandboxValidator.run_targeted_tests` in an ephemeral worktree.
   - Asserts that `parse_test_diagnostics` produces a `DiagnosticPayload` containing:
     - `test_file == "tests/test_auth.py"`
     - `test_case == "test_login_valid"`
     - `line_number == 54`
     - `failure_type == "TypeError"`
     - `implicated_symbols == ["login"]`

3. `test_agentic_refinement_multi_file_patch_synthesis`:
   - Invokes `build_refinement_prompt` with the captured $E_k$ and the bounded AST slice.
   - Verifies that the prompt contains the exact `--- VALIDATION FAILURE TRACE ---`, the failure line coordinate, and the focused AST block.
   - Simulates the refinement completion and verifies that `parse_multi_file_unified_diff` extracts separate hunks for `auth.py` and `tests/test_auth.py`.

4. `test_anti_gaming_defense_on_complementary_test_patch`:
   - Validates that an honest call-site update (`login("alice", tenant_id="t1")`) passes with `result.passed is True` and `deleted_assertions_count == 0`.
   - Validates that an adversarial patch (deleting `assert user.is_authenticated is True`) is blocked with `result.passed is False` and `ANTI_GAMING_WARNING`.

5. `test_atomic_multi_file_guarded_apply_and_revalidation`:
   - Applies the validated multi-file patch to the working tree.
   - Confirms that both `auth.py` and `tests/test_auth.py` are updated on disk.
   - Executes the targeted test suite and confirms all tests pass.
   - Triggers `rollback_suggestion` and confirms both files are restored to their pristine original bytes.

6. `test_mcp_full_closed_loop_code_surgery`:
   - Uses `call_tool` from `gdss.mcp.server` to execute:
     1. `gdss_get_impact_closure` (returns closure nodes and target tests).
     2. `gdss_validate_patch` (validates multi-file Tree-sitter AST).
     3. `gdss_check_anti_gaming` (verifies assertion preservation on test diff).
     4. `gdss_sandbox_validate_patch` (executes worktree validation).

---

### Harness & Configuration Alignment

#### [MODIFY] `harness/state/progress.md`
- Record entry for the new integration test suite and closed-loop verification results.

#### [MODIFY] `harness/state/session-handoff.md`
- Document the new test scenarios and integration coverage.

---

## Verification Plan

### Automated Tests
Run the newly created integration tests and the full verification gate:
```bash
# 1. Run the new integration test suite directly
pytest tests/integration/test_semantic_impact_code_surgery.py -v

# 2. Run static layer sensors
bash harness/sensors/lint.sh
bash harness/sensors/typecheck.sh
python harness/sensors/architecture_fitness.py
python harness/sensors/dsa_fitness.py

# 3. Run full verification gate (backend + frontend)
bash harness/verify.sh
```

### Manual Verification
1. Inspect test execution output to verify that real ephemeral worktrees are created and cleaned up.
2. Confirm that multi-file unified diff parsing cleanly anchors onto files with zero prior Git diff hunks.
3. Verify that anti-gaming correctly flags both Python assertions and multi-language assertion patterns.

