---
name: Phase4 conflict tensor
overview: "Build the Conflict Tensor Engine in `gdss/conflict/`: an operator-type commutativity table, pairwise operator commutativity, and the sparse Ω_{ij} branch-interaction matrix (deterministic, no drift import — drift magnitudes passed in by caller). Wire a `gdss tensor` CLI command. TDD, one vertical slice at a time."
todos:
  - id: slice1-commutativity
    content: "TDD: commutativity.py — operator-type table + pairwise classify (test first)"
    status: completed
  - id: slice2-interference
    content: "TDD: operator_interference() over op-sets using classify (test first)"
    status: completed
  - id: slice3-tensor
    content: "TDD: tensor.py — TensorEngine.compute sparse Omega_{ij} + merge_risk (test first)"
    status: completed
  - id: slice4-cli
    content: "TDD: gdss tensor CLI command + do_tensor Rich matrix rendering (test first)"
    status: completed
  - id: slice5-verify
    content: Run verify.sh green; mark phase4-tensor done; update progress.md + session-handoff.md
    status: completed
isProject: false
---

# Phase 4 — Conflict Tensor Engine (Ω_{ij} + commutativity)

## Goal

Deliver `phase4-tensor` from [`harness/state/feature_list.json`](harness/state/feature_list.json) (lines 112-122):

> `gdss/conflict/*` computes Omega_{ij} + commutativity table; tests green

Deps satisfied: `phase3-drift` is `done`.

## Architecture constraint (load-bearing)

`gdss/conflict` is **layer 7**; `gdss/drift` is **layer 8**. Conflict **must not import drift** (enforced by [`tests/conflict/test_conflict_architecture.py`](tests/conflict/test_conflict_architecture.py) and [`harness/sensors/architecture_fitness.py`](harness/sensors/architecture_fitness.py)). Same pattern as the existing [`ConflictProbabilityEstimator`](gdss/conflict/probability.py): the CLI/daemon composes drift snapshots + tensor; the conflict layer stays pure and accepts `drift_magnitudes: dict[str, float]` (or per-pair floats) as a caller-supplied input.

Allowed imports for new conflict code: `gdss.core.transform_types`, `gdss.core.trajectory` (layer 4), `gdss.graph.code_graph` (layer 5). **No** `gdss.drift`, `gdss.embeddings`, `gdss.ai`.

## Math (from vision doc + glossary)

- Commutativity `[T_i, T_j] = 0` → order-independent (safe merge); `!= 0` → interference.
- Ω_{ij} overlap energy (vision doc L1171-1184): `same_file × 0.2 + same_function × 0.5 + same_symbol × 0.7 + dependency_overlap × 0.4`.
- `R_merge = Σ_{i,j} Ω_{ij}` (vision doc L237-238).
- Keep it deterministic and sparse: most branch pairs have zero overlap → dict-of-dicts, not dense N×N.

```mermaid
flowchart TD
  subgraph caller [CLI / daemon — composes layers]
    drift[DriftEngine.snapshot magnitudes]
    traj[extract_trajectory_operators per branch]
  end
  subgraph conflict [gdss/conflict — NEW, layer 7, pure]
    comm[commutativity.py<br/>operator-type table + pairwise]
    tensor[tensor.py<br/>Omega_{ij} sparse matrix]
  end
  caller -->|"list[SemanticOperator] per branch"| comm
  caller -->|"list[SemanticOperator] per branch"| tensor
  caller -->|"drift_magnitudes: dict[str,float]"| tensor
  comm --> tensor
  tensor --> cli["gdss tensor — Rich matrix + R_merge"]
```

## Implementation (TDD, vertical slices)

### Slice 1 — Commutativity table (operator-type interaction)

New file [`gdss/conflict/commutativity.py`](gdss/conflict/commutativity.py).

- A static operator-type interaction table: for each pair `(OperatorType, OperatorType)` applied to the **same symbol**, classify as `COMMUTE` (order-independent), `INTERFERE` (non-commutative), or `INDEPENDENT` (different symbols / no contact). Ground it in operator semantics:
  - `RENAME_*` × `DELETE_*` (same symbol) → `INTERFERE` (rename-then-delete ≠ delete-then-rename)
  - `RENAME_*` × `RENAME_*` (same from/to) → `INTERFERE`
  - `MODIFY_*` × `MODIFY_*` (same symbol) → `COMMUTE` (both modify; merge may conflict but order is symmetric)
  - `ADD_*` × `ADD_*` (different symbols) → `INDEPENDENT`
- Public API:
  - `class CommutativityClass(str, Enum): COMMUTE / INTERFERE / INDEPENDENT`
  - `def classify(op_a: SemanticOperator, op_b: SemanticOperator) -> CommutativityClass` — pairwise on instances (uses target names + the type table)
  - `def commutativity_table() -> dict[tuple[OperatorType, OperatorType], CommutativityClass]` — the static type×type table

Test first: [`tests/conflict/test_commutativity.py`](tests/conflict/test_commutativity.py) — rename+delete same symbol → INTERFERE; modify+modify same symbol → COMMUTE; add+add different files → INDEPENDENT; table is symmetric for same-type pairs.

### Slice 2 — Pairwise operator-set interference count

In `commutativity.py`:

- `def operator_interference(branch_ops: Sequence[SemanticOperator], other_ops: Sequence[SemanticOperator]) -> tuple[int, int]` → `(interfering_pairs, total_contact_pairs)`. Uses `classify` per pair. O(B×R) is acceptable for small op-sets; document the complexity. Build a `dict[str, list[SemanticOperator]]` keyed by target name to avoid a full cartesian when sets are large (DSA rule).

Test first: two op-sets with a rename/delete collision → `(1, 1)`; disjoint sets → `(0, 0)`.

### Slice 3 — Ω_{ij} tensor engine

New file [`gdss/conflict/tensor.py`](gdss/conflict/tensor.py).

- `@dataclass(frozen=True) class TensorEntry: i: str; j: str; omega: float; reasons: tuple[str, ...]`
- `@dataclass(frozen=True) class ConflictTensor: branches: tuple[str, ...]; entries: dict[tuple[str, str], TensorEntry]; merge_risk: float`
- `class TensorEngine`:
  - `__init__(self, *, w_file=0.2, w_function=0.5, w_symbol=0.7, w_dependency=0.4)` (vision-doc weights)
  - `def compute(self, branch_ops: dict[str, list[SemanticOperator]], drift_magnitudes: dict[str, float], impact_sets: dict[str, set[str]] | None = None) -> ConflictTensor`
  - For each unordered branch pair `(i, j)`:
    - `same_file` = `len(files_i & files_j) > 0`
    - `same_function` = symbol-name overlap on `MODIFY/DELETE` targets
    - `same_symbol` = full target-name overlap
    - `dependency_overlap` = `len(impact_i & impact_j)` if impact_sets supplied else 0
    - `interference` from slice 2 (interfering_pairs / max(1, contact_pairs))
    - `omega = w_file·file + w_function·func + w_symbol·sym + w_dependency·dep + interference·w_interfere` (clamped to [0,1])
    - Only store entries with `omega > 0` (sparse)
  - `merge_risk = Σ entries.omega` (includes symmetric pairs once — document the convention)
  - Diagonal `Ω_{ii}` = `drift_magnitudes[branch]` (branch self-energy) if supplied

Test first: [`tests/conflict/test_tensor.py`](tests/conflict/test_tensor.py) — two branches sharing a modified file → `omega > 0`; disjoint branches → no entry; `merge_risk` equals sum; drift on diagonal; sparse (only non-zero entries present).

### Slice 4 — CLI `gdss tensor`

- [`gdss/cli/main.py`](gdss/cli/main.py): add `@app.command() def tensor(...)` mirroring `drift`/`alerts` (after `alerts`, ~L101), delegating via `run_shell(repo, f"tensor {ref}")`.
- [`gdss/cli/start.py`](gdss/cli/start.py): add `do_tensor(self, arg)` next to `do_drift` (~L516). Reuse the branch-enumeration + `extract_trajectory_operators` pattern already in `do_drift` (L440-515), then build the tensor:
  - `engine = DriftEngine(...)` → `snap = engine.snapshot(branch, ref)` per branch → `drift_magnitudes[branch] = snap.magnitude.magnitude`
  - `branch_ops[branch] = extract_trajectory_operators(..., ref_branch=ref, head=branch)`
  - `TensorEngine().compute(branch_ops, drift_magnitudes)` → render Rich `Table` (N×N matrix with Ω values) + a line for `R_merge`. Replace the "Conflict P is heuristic (not Omega tensor)" footnote (L513-515) with the real tensor when `tensor` is invoked; keep `drift` as-is.
- Single-attractor guard: reuse `is_single_attractor_trajectory` (L448) — print "no other branches" and return.

Test first: extend [`tests/cli/test_drift_cli.py`](tests/cli/test_drift_cli.py) pattern — add `tests/cli/test_tensor_cli.py` asserting `gdss tensor` runs over the fixture repo without error and prints a matrix row. (CLI smoke via [`harness/sensors/cli_smoke.sh`](harness/sensors/cli_smoke.sh) is the Layer-3 gate.)

### Slice 5 — Verify + harness state

- `bash harness/verify.sh` green (ruff, mypy, architecture_fitness, dsa_fitness, pytest, cli_smoke, frontend hard gates).
- Update [`harness/state/feature_list.json`](harness/state/feature_list.json): `phase4-tensor` → `done` + `evidence`.
- Append dated entry to [`harness/state/progress.md`](harness/state/progress.md) with verify output (Ω matrix sample, R_merge, test counts).
- Update [`harness/state/session-handoff.md`](harness/state/session-handoff.md): next is `frontend-local-api` (deps satisfied) or `phase5-ai`.

## Out of scope

- Daemon `"conflict"` event emission (separate wiring step)
- Embeddings-based Ω (geometric form `⟨v_i, P_{j→i}(v_j)⟩`) — keep deterministic for phase4
- Frontend visualization of the tensor (later `frontend-*` phase)
- Editing existing `gdss/conflict/probability.py` (additive only; `do_drift` keeps using the heuristic)

## Success evidence (for progress.md)

- `tests/conflict/test_commutativity.py`, `test_tensor.py` green
- `tests/cli/test_tensor_cli.py` green; `cli_smoke.sh` green
- `architecture_fitness.py`: layer direction + two-brain still hold (no `gdss.drift` import under `gdss/conflict/`)
- `bash harness/verify.sh` → ALL LAYERS GREEN
