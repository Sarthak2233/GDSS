# Implementation Plan: Phase 5a Agent Orchestration & Convergence Delivery

## 1. Context & Architecture

GDSS is designed to detect semantic collisions across concurrent PR branches, calculate non-commutative operator interactions ($\Omega_{ij}$), and suggest verified convergence patches.

The user selected the phased roadmap progression:
1. **Phase 5a (Agent Orchestration & Audited Suggestion State)**: Orchestrates the pipeline (analysis -> topology -> optional drafting -> sandboxed validation -> immutable `sug_...` ID caching at human review checkpoints).
2. **Phase 6a (Human-Approved Local Apply)**: Guarded CLI command `gdss apply <SUGGESTION_ID>` with preflight freshness checks, atomic rollback, and syntax verification.
3. **Phase 1.8b (GitHub Actions Delivery & 1-Click Suggestion Button)**: Cloud PR audit posting sticky collision radar reports and inline review comments with native GitHub ````suggestion ```` blocks.

---

## 2. Phase 5a Scope & Invariants (`phase5a-agent-orchestration`)

### Invariants:
- **Zero Token Bleed & Model-Free by Default**: Operates 100% deterministically without requiring an LLM; optional LLM drafting hooks into existing providers (vLLM, Ollama, OpenRouter, GitHub Models).
- **Two-Brain Purity**: Lives in `gdss/ai/` (probabilistic/orchestration layer). Deterministic layers (`core`, `graph`, `conflict`, `watcher`, `mcp`) never import `gdss/ai`.
- **Optional Dependency**: Built-in pure Python state machine / DAG runner requiring zero extra dependencies. If `langgraph` is installed, provides an optional LangGraph-compatible graph export without breaking offline `pip install gdss`.
- **Audited State**: Serializes metadata-only JSON to `.gdss/suggestions/<suggestion_id>.json`. Never mutates Git state, commits, or user files.
- **Explicit Human Checkpoint**: Always stops in an `AWAITING_HUMAN_REVIEW` checkpoint.

---

## 3. Detailed Component Design for Phase 5a

### A. Immutable Suggestion ID & Audited Store (`gdss/ai/suggestion_store.py`)
- **Deterministic ID Generation**:
  $$\text{suggestion\_id} = \text{"sug\_"} + \text{sha256}(commit\_sha, file\_path, line\_start, line\_end, operator, strategy)[:12]$$
- **Store Operations**:
  - `save_suggestion(suggestion, repo_root)`: Writes `.gdss/suggestions/<suggestion_id>.json`.
  - `load_suggestion(suggestion_id, repo_root) -> Suggestion`: Reads suggestion and verifies schema.
  - `list_suggestions(repo_root) -> list[SuggestionSummary]`: Lists active cached suggestions.
  - `is_stale(suggestion, current_head_sha) -> bool`: Verifies target branch HEAD hasn't moved.

### B. Orchestration Workflow (`gdss/ai/orchestration.py`)
A state-graph runner managing the convergence lifecycle:
```
  [Input Context]
         │
         ▼
  Node 1: analyze_conflicts  (Ranked Tensor entries + ConflictTopology + Anchors)
         │
         ▼
  Node 2: draft_resolutions  (Model-free templates or optional local LLM provider)
         │
         ▼
  Node 3: validate_sandbox   (Ephemeral worktree dry-run: syntax, types, tests)
         │
         ▼
  Node 4: audit_checkpoint   (Assigns sug_... IDs, saves to .gdss/suggestions/)
         │
         ▼
  [AWAITING_HUMAN_REVIEW]    (Paused; ready for `gdss apply` or GitHub 1-click button)
```

- **Graph State Object (`ConvergenceState`)**:
  - `repo_path: str`
  - `reference_branch: str`
  - `target_commit: str`
  - `ranked_entries: list[TensorEntry]`
  - `suggestions: list[Suggestion]`
  - `validated_suggestions: list[Suggestion]`
  - `checkpoint: Literal["analyzing", "drafting", "validating", "awaiting_human_review", "completed"]`
  - `errors: list[str]`

- **Optional LangGraph Adapter**:
  - If `langgraph` is present, `get_langgraph_workflow()` compiles a `StateGraph(ConvergenceState)`.
  - If absent, executes seamlessly via `OrchestrationPipeline.run()`.

---

## 4. Test-First (TDD) Plan for Phase 5a

Following the **three-layer validation hierarchy**:
1. **Unit Tests (`tests/ai/test_suggestion_store.py`)**:
   - Test ID generation stability.
   - Test saving and loading suggestions from `.gdss/suggestions/`.
   - Test target commit staleness detection (`is_stale`).
2. **Integration Tests (`tests/ai/test_orchestration.py`)**:
   - Test model-free end-to-end execution on Git test fixture.
   - Test pipeline pausing at `AWAITING_HUMAN_REVIEW`.
   - Test sandboxed validation integration when `--validate` flag is enabled.
   - Test optional LangGraph import degradation (runs without error when `langgraph` not installed).
3. **Verification Gate**:
   - `bash harness/sensors/lint.sh` (Ruff)
   - `bash harness/sensors/typecheck.sh` (Mypy)
   - `python harness/sensors/architecture_fitness.py` (Two-brain purity)
   - `bash harness/sensors/run_tests.sh` (Pytest)

---

## 5. Downstream Handoff (Phase 6a & Phase 1.8b)

Once Phase 5a outputs audited `sug_...` files:
1. **Phase 6a (`gdss apply <SUG_ID>`)**:
   - Reads `.gdss/suggestions/<SUG_ID>.json`.
   - Runs preflight check (ensures current repo HEAD matches `target_commit`).
   - Applies the patch into the working tree unstaged.
   - Runs post-apply syntax validation and saves `.gdss/rollback/<SUG_ID>.patch`.
2. **Phase 1.8b (`phase-d-github-actions`)**:
   - Reads the validated suggestions.
   - Formats GitHub Review Comment payloads with the ````suggestion ```` block.
   - Uses `GITHUB_TOKEN` to comment on GitHub PRs with the green 1-click commit button.
