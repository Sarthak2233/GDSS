# GDSS Progress Log

Append a dated entry each session. Newest at the top. Record evidence (verify
output), not just claims.

---

## 2026-07-17 - Verify gate: lint + typecheck cleanup

`bash harness/verify.sh` was failing at Layer 1 because ruff/mypy are now
installed (previously SKIP) and reported pre-existing style/type debt.

Fixed:
- `ruff check --fix .` (~484 autofixes) plus 7 manual lint fixes
- 20 mypy errors (annotations, Optional narrowing, unused type: ignore, etc.)

Evidence (`bash harness/verify.sh`):
- Layer 1: lint OK; typecheck OK; architecture OK; DSA OK
- Layer 2: pytest 53 passed, 3 skipped
- Layer 3: cli-smoke OK
- Result: ALL LAYERS GREEN (exit 0)

---
## 2026-07-17 - Phase 2: Semantic Embedding Layer

Implemented probabilistic Layer 6 (`gdss/embeddings/`):
- DeterministicBagEncoder (offline default) + optional OnnxMiniLMEncoder
- Content-hash LRU EmbeddingCache; vectorized cosine similarity
- Branch tip aggregation (`aggregate_branch_tip`, assistive distance helper)
- FAISS VectorStore (`IndexFlatIP`) with numpy fallback; persist under `.gdss/vectors/`
- CLI: `gdss similar`, `gdss reindex`; status shows assistive embedding tip note
- Optional extras: `pip install -e ".[embeddings]"` (faiss-cpu, onnxruntime)
- Two-brain purity preserved (architecture fitness OK)

Evidence (`bash harness/verify.sh`):
- Layer 1: architecture OK; DSA OK
- Layer 2: pytest 55 passed, 1 skipped
- Layer 3: cli-smoke OK (includes similar)
- Result: ALL LAYERS GREEN (exit 0)

---
## 2026-07-13 - Phase 1.1 Transcendence (Correctness + Honesty)

Hardened Phase 1.1 into a trustworthy semantic observation layer (no Phase 2 embeddings).

**Workstream A — AST/transform correctness**
- Fixed UTF-8 Tree-sitter byte/str slicing in `ASTParser._get_node_text`.
- Symbol maps keyed by `(parent_class, name)` to prevent multi-class collisions.
- Wired fingerprint buckets; reject near-empty stub renames and non-identifier names.

**Workstream B — CLI honesty**
- Remote row is ahead/behind or N/A (never `remote_aware` → "DRIFT DETECTED").
- Prompt `Δ` means local uncommitted semantic delta only.
- `status --ref` honored; `config ref` persists via hierarchy DB.
- Status sections: attractor/remote, trajectory since reference, uncommitted semantic delta.
- Single-attractor honesty note when only one local branch equals ref.

**Workstream C/E/F — cache, languages, scale**
- Content-hash LRU cache for `parse_file(content=...)`.
- Language registry + Go grammar (`tree-sitter-go`).
- `analyze` progress callbacks + skipped-unsupported summary.

Evidence (`bash harness/verify.sh`):
- Layer 1: architecture OK; DSA OK
- Layer 2: pytest 37 passed
- Layer 3: cli-smoke OK (asserts no "DRIFT DETECTED"; section titles present)
- Result: ALL LAYERS GREEN (exit 0)
---
 
---
## 2026-07-07 - Interactive Shell Diff Command Enhancement (session)

Enhanced the shell's `diff` command (`do_diff` in `gdss/cli/start.py`) to correctly display diffs against the working directory (staged, unstaged, and untracked changes) rather than strictly comparing branch-to-branch commits.
- Modified `do_diff` to perform `commit_base.diff(None)` (commit to working tree diff) and include `self.observer.repo.untracked_files` as added files.
- Upgraded the modified files loop to read updated contents directly from the filesystem (working tree) if available, with a fallback to `HEAD`, so that uncommitted changes are parsed and their semantic operators are extracted.
- Improved tracking of moved/renamed files during diff by mapping the old path to the new path, enabling correct symbol AST parsing and operator extraction.

Evidence (`bash harness/verify.sh` & manual run):
- Layer 1 static: Architecture fitness OK; DSA fitness OK (0 violations)
- Layer 2 runtime: pytest 24 passed
- Layer 3 end-to-end: cli-smoke OK
- Command `gdss diff` now correctly prints all untracked, uncommitted, and committed changes, including detailed semantic operators.

---

## 2026-07-07 - Monokai Theme Color Fix (session)

Fixed fatal crash during shell rendering (e.g. running `diff`) when the `monokai` theme is selected.
- Replaced invalid color names (`bright_pink`, `bright_orange`, `bright_purple`) in the `monokai` theme registry in `gdss/cli/start.py` with standard, valid CSS hexadecimal codes (`#f92672`, `#fd971f`, `#ae81ff`).

Evidence (`bash harness/verify.sh`):
- Layer 1 static: Architecture fitness OK; DSA fitness OK
- Layer 2 runtime: pytest 24 passed
- Layer 3 end-to-end: cli-smoke OK
- Result: ALL LAYERS GREEN (exit 0)

---

## 2026-07-07 - REPL Shell Rich Prompt Rendering & Status Indicators (session)

Implemented rich visual prompt rendering and dynamic status indicator features in the interactive shell (`gdss` command CLI):
- Overrode the `cmdloop` method of `GDSSShell` to prompt the user using Rich's `console.input` instead of the default `input()`. This correctly renders Rich markup in the prompt.
- Refactored prompt layout to `gdss(branch:<name>) <status> ▶ ` to clearly indicate the current Git branch.
- Added dynamic status checking to query git working tree and semantic drift:
  - 🟢 `●` (success theme color) indicates clean state (with remote check).
  - 🟡 `✱` (warning theme color) indicates uncommitted modifications / untracked files without semantic changes.
  - 🔴 `Δ` (error theme color) indicates code files with semantic changes (extracted operators) or remote drift.
- Resolved a DSA static analysis violation concerning repeated calls to `self.observer.is_valid()` in `_get_status_indicator`.

Evidence (`bash harness/verify.sh`):
- Layer 1 static: Architecture fitness OK; DSA fitness OK (0 violations)
- Layer 2 runtime: pytest 24 passed
- Layer 3 end-to-end: cli-smoke OK
- Result: ALL LAYERS GREEN (exit 0)

---

## 2026-07-07 - Dependency Cleanup & Test Fix (session)

Resolved test collection failure in Layer 2 tests due to missing `yaml` dependency.

Removed unused `yaml` imports from:
- `gdss/runtime/hierarchy.py`
- `gdss/runtime/registry.py`

Refactored `tests/runtime/test_registry.py` to use a native Python dictionary instead of `yaml.safe_load(config)`. This removes the requirement for `PyYAML` and keeps the dependency set minimal.

Evidence (`bash harness/verify.sh`):
- Layer 1 static: Architecture fitness OK; DSA fitness OK
- Layer 2 runtime: pytest 24 passed (all tests green)
- Layer 3 end-to-end: cli-smoke OK
- Result: ALL LAYERS GREEN (exit 0)

---

## 2026-07-06 - Phase 1.1: Rigor Refactor (session)

Completed Phase 1 semantic foundation refactor: stable symbol identity, executable
operators, structural fingerprints, block-level modify details, and graph
invariance across file moves.

Created:
- `gdss/core/structural_fingerprint.py` — Levenshtein distance, normalized
  similarity, fingerprint buckets
- `gdss/core/symbol_identity.py` — deterministic `symbol_id` (position-independent)
- `gdss/graph/operator_engine.py` — `apply_operator()` / `invert_operator()` for
  core add/delete/rename/modify ops

Modified:
- `gdss/core/transform_types.py` — `BodyBlock`, stable `CodeSymbol` identity,
  `SemanticOperator` symbol_id fields
- `gdss/core/ast_parser.py` — structural tokens + body blocks per symbol
- `gdss/core/transform_extractor.py` — AST-token Levenshtein rename detection,
  block-level `changed_blocks` in MODIFY_FUNCTION
- `gdss/graph/code_graph.py` — node IDs = `symbol_id`, `chart_location` metadata,
  `_file_nodes` / `_symbol_index` indexes, `reverse(copy=False)`

Tests added/updated:
- `tests/test_transform_extractor.py` — formatter-invariant rename, block-level
  modify, Levenshtein unit test
- `tests/test_code_graph.py` — stable identity, file-move preservation
- `tests/test_operator_algebra.py` — commutativity identity (apply + invert)

Evidence (`bash harness/verify.sh`):
- Layer 1 static: Architecture fitness OK; DSA fitness OK (4 violations fixed)
- Layer 2 runtime: pytest 21 passed
- Layer 3 end-to-end: cli-smoke OK
- Result: ALL LAYERS GREEN (exit 0)

Remaining risks:
- `finding-call-resolution-quadratic` partially resolved (symbol index; import
  edge scan remains)
- `finding-no-parser-cache` and `finding-flat-symbol-list` still open
- lint/typecheck SKIP (ruff/mypy not installed)

---

## 2026-06-16 - Phase 0: Distributed Runtime Foundation (session 1)

Implemented the GDSS Distributed Runtime Foundation. Redesigned the core to
treat GitHub/Remote as the authoritative source of truth.

Created:
- Layer 0 & 3: `gdss/runtime/registry.py`, `gdss/runtime/hierarchy.py`
- Layer 1 & 2: `gdss/runtime/local_observer.py`, `gdss/runtime/remote_monitor.py`
- Layer 4 & 5: `gdss/runtime/event_bus.py`, `gdss/runtime/context_engine.py`
- Layer 6: `gdss/cli/start.py` (Interactive Shell), `gdss/cli/main_new.py`
- Storage: `gdss/storage/db.py` (SQLite schema)

Evidence (`bash harness/verify.sh`):
- Layer 1 static: Architecture fitness OK; DSA fitness OK (fixed time.time() cache).
- Layer 2 runtime: pytest 6 passed (all new tests green).
- Result: ALL LAYERS GREEN (exit 0).

---

## 2026-06-05 - Harness bootstrap (session 0)

Installed the GDSS harness engineering layer (guides + sensors + state +
lifecycle) around the existing codebase. No existing `gdss/` or `tests/` source
was modified.

Created:

- Guides: `AGENTS.md`, `.cursor/rules/*.mdc` (context, architecture invariants,
  math glossary, python conventions, verification/TDD, harness discipline),
  `.cursor/skills/*` (tdd, add-semantic-operator, implement-gdss-phase,
  verify-changes, audit-harness).
- Sensors: `.cursor/hooks/*` (block-dangerous-git, run-fast-sensors, audit-log)
  wired in `.cursor/hooks.json`; `harness/verify.sh` three-layer gate;
  `harness/sensors/*` (lint, typecheck, run_tests, cli_smoke,
  architecture_fitness.py); `ruff.toml`, `mypy.ini`.
- State/lifecycle: `harness/init.sh`, `harness/state/*`, `harness/README.md`.

Evidence (`bash harness/verify.sh`):

- Layer 1 static: architecture fitness OK; lint/typecheck SKIP (ruff/mypy not
  installed - install to make them hard gates).
- Layer 2 runtime: pytest 6 passed.
- Layer 3 end-to-end: cli_smoke OK.
- Result: ALL LAYERS GREEN (exit 0).

Harness finding (the gate paid for itself immediately): the Layer 3 end-to-end
run surfaced a real pre-existing bug in `gdss/cli/main.py:228` - `gdss status`
crashes (`TypeError ... not NoneType`) when a branch **renames** a function,
because rename operators have `name=None`. Logged as
`finding-rename-downstream-crash` in `feature_list.json`. Fixing it needs a
source edit, so it is deferred until the user authorizes changes to `gdss/`.

Next: see `session-handoff.md`.
