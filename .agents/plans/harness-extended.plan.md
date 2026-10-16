---
name: ""
overview: ""
todos: []
isProject: false
---

# DSA Optimization Layer for GDSS Harness

Incorporate Data Structures & Algorithms optimization principles into the GDSS harness so that **every time an agent writes code**, it is guided toward algorithmically efficient patterns and validated against known anti-patterns.

## User Review Required

> [!IMPORTANT]
> This is a **harness-only** change. No source code under `gdss/` or `tests/` will be modified. The DSA layer adds a new **feedforward guide** (Cursor rule), a new **skill** (on-demand workflow), a new **sensor** (automated anti-pattern detection), and updates to existing harness docs. Existing files are preserved; all changes are additive.

> [!WARNING]
> The research identified **6 concrete DSA anti-patterns** already present in the codebase (e.g., O(D×A) rename detection, full graph copy on every impact query). These will be **documented as known technical debt** in the harness findings, NOT fixed in this sprint. They become backlog items that the agent must avoid repeating in new code.

## Proposed Changes

### New Guide: DSA Optimization Rule

#### [NEW] [.cursor/rules/35-dsa-optimization.mdc](file:///home/sbasnet/projects/GDSS/.cursor/rules/35-dsa-optimization.mdc)

A new always-on Cursor rule (numbered `35` to slot between Python conventions `30` and verification `40`). Enforces DSA-aware coding for every `.py` file. Contains:

- **Complexity Budget**: Every public function must have its time/space complexity justified. O(N²) or worse requires explicit rationale.
- **Data Structure Selection Matrix**: A GDSS-specific lookup table mapping common operations to preferred structures:

  | Operation                 | Preferred Structure                         | Avoid                                            |
  | ------------------------- | ------------------------------------------- | ------------------------------------------------ |
  | Symbol lookup by name     | `dict[str, CodeSymbol]` (O(1))              | Linear scan of `list` (O(N))                     |
  | Membership test           | `set` / `frozenset` (O(1))                  | `x in list` (O(N))                               |
  | Graph traversal (impact)  | Cached reverse graph / `nx.descendants`     | `g.reverse(copy=True)` per call                  |
  | Rename detection          | Pre-computed body fingerprints + threshold  | Pairwise `SequenceMatcher` (O(D×A×L))            |
  | Ordered iteration         | `list` / `tuple`                            | `dict` (insertion order, but semantically wrong) |
  | Frequency counting        | `collections.Counter`                       | Manual dict increment loops                      |
  | Priority-based processing | `heapq`                                     | Repeated `min()` on list                         |
  | Memoization               | `functools.lru_cache` / explicit cache dict | Recomputing from scratch                         |
  | File→nodes index          | `dict[str, set[NodeID]]`                    | O(N) scan to find nodes by file                  |

- **GDSS-Specific Patterns**: Graph caching strategies, incremental AST update patterns, embedding vector batch operations.
- **Anti-Pattern Catalog**: Documented patterns to avoid, each with WHAT/WHY/BETTER structure.

---

### New Skill: DSA Optimization Workflow

#### [NEW] [.cursor/skills/dsa-optimize/SKILL.md](file:///home/sbasnet/projects/GDSS/.cursor/skills/dsa-optimize/SKILL.md)

On-demand workflow an agent invokes when writing performance-sensitive code or refactoring existing modules. Steps:

1. **PROFILE**: Identify the hot path and its current complexity.
2. **SELECT**: Choose the optimal data structure from the selection matrix.
3. **IMPLEMENT**: Write the optimized version with complexity annotations.
4. **BENCHMARK** (optional): Compare before/after on representative inputs.
5. **DOCUMENT**: Add docstring noting the complexity choice and rationale.

Includes a **GDSS DSA Cheat Sheet** section with concrete patterns for each layer:

- **Layer 2 (Watcher)**: Efficient diff caching, commit batch processing.
- **Layer 3-4 (Core)**: Symbol indexing, transform algebra composition with hash-based dedup.
- **Layer 5 (Graph)**: Incremental graph updates, cached reverse graphs, indexed node lookups.
- **Layer 6 (Embeddings)**: Vector batch operations, LRU caching for embeddings, approximate nearest neighbor.
- **Layer 7-8 (Conflict/Drift)**: Sparse tensor representation, incremental drift updates.

---

### New Sensor: DSA Anti-Pattern Detector

#### [NEW] [harness/sensors/dsa_fitness.py](file:///home/sbasnet/projects/GDSS/harness/sensors/dsa_fitness.py)

A static analysis sensor (similar to `architecture_fitness.py`) that scans `gdss/**/*.py` for common DSA anti-patterns. Uses Python's `ast` module to detect:

1. **Linear membership tests**: `x in some_list` where `some_list` is assigned as a list → suggest `set`.
2. **Nested loops over same collection**: O(N²) patterns without justification comment.
3. **Repeated `.reverse(copy=True)`**: Graph copy anti-pattern.
4. **Missing `lru_cache`**: Pure functions called multiple times with same args.
5. **Dict-building via append+search**: Building a list then searching it, instead of building a dict directly.

Output format: WHAT / WHY / FIX (agent-oriented). Exit 0 = clean, exit 1 = violations found.

> [!NOTE]
> The sensor will initially flag known existing issues in the codebase. We'll add a `# dsa:ignore` comment-based suppression mechanism so existing code can be grandfathered without blocking the pipeline, while new code must pass clean.

---

### Harness Integration

#### [MODIFY] [harness/verify.sh](file:///home/sbasnet/projects/GDSS/harness/verify.sh)

Add `dsa_fitness.py` as a **Layer 1 static sensor**, running after `architecture_fitness.py`:

```diff
+ echo "── DSA fitness ──"
+ python harness/sensors/dsa_fitness.py || exit 1
```

#### [MODIFY] [harness/README.md](file:///home/sbasnet/projects/GDSS/harness/README.md)

Add the DSA layer to the harness map documentation. Explain how the guide (rule `35`), skill (`dsa-optimize`), and sensor (`dsa_fitness.py`) form a complete feedforward+feedback loop for algorithmic quality.

#### [MODIFY] [AGENTS.md](file:///home/sbasnet/projects/GDSS/AGENTS.md)

Add a new golden rule:

```
- **DSA-first coding.** Choose data structures deliberately. Every public function
  should have justifiable time/space complexity. See `.cursor/rules/35-dsa-optimization.mdc`
  for the selection matrix and `.cursor/skills/dsa-optimize/` for the workflow.
```

#### [MODIFY] [harness/state/feature_list.json](file:///home/sbasnet/projects/GDSS/harness/state/feature_list.json)

Add the 6 identified DSA anti-patterns as `harness_findings` entries (technical debt backlog):

1. `finding-graph-reverse-copy` — `code_graph.py:get_downstream_impact()` copies entire graph per call
2. `finding-rename-quadratic` — `transform_extractor.py` O(D×A) pairwise similarity
3. `finding-call-resolution-quadratic` — `code_graph.py:resolve_calls()` O(F²) nested iteration
4. `finding-stale-node-scan` — `code_graph.py:add_file_symbols()` O(N) scan for stale nodes
5. `finding-no-parser-cache` — AST parser recomputes from scratch every time
6. `finding-flat-symbol-list` — `ast_parser.py` returns flat list, no indexed lookup

---

### Updated Sprint Plan

#### [MODIFY] [sprint_phase1_cli_beta.plan.md](file:///home/sbasnet/projects/GDSS/.cursor/plans/sprint_phase1_cli_beta.plan.md)

Add a new sub-phase entry:

```
### Sub-Phase: DSA Optimization Harness
- [x] Create `.cursor/rules/35-dsa-optimization.mdc` (feedforward guide)
- [x] Create `.cursor/skills/dsa-optimize/SKILL.md` (on-demand workflow)
- [x] Create `harness/sensors/dsa_fitness.py` (feedback sensor)
- [x] Wire sensor into `harness/verify.sh`
- [x] Document 6 existing anti-patterns as harness findings
```

## Verification Plan

### Automated Tests

- Run `python harness/sensors/dsa_fitness.py` and confirm it detects at least 1 known anti-pattern in the existing codebase (proving the sensor works).
- Run `bash harness/verify.sh` and confirm the new sensor is wired in and the pipeline still completes (existing anti-patterns should be suppressed with `# dsa:ignore` or baseline mechanism).

### Manual Verification

- Review `35-dsa-optimization.mdc` to confirm the data structure selection matrix covers all GDSS layers.
- Review `dsa-optimize/SKILL.md` to confirm the workflow is actionable and layer-specific.
- Confirm `AGENTS.md` golden rules include DSA-first coding.

