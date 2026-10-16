---
description: Always apply this rule to enforce Data Structures & Algorithms optimization principles.
globs: **/*.py
---
# DSA Optimization Rule

Every time you write or modify Python code, you must apply rigorous Data Structures & Algorithms (DSA) optimization principles. Code quality is not just about syntax; it is about algorithmic efficiency.

## 1. Complexity Budget
- **Time/Space Justification**: Every thing must be designed with an awareness of its asymptotic time and space complexity.
- **O(N²) or worse**: If you write an O(N²) (or worse) algorithm, you **must** include a comment explaining why it is unavoidable or acceptable given the input size constraints.

## 2. Data Structure Selection Matrix

| Operation | Preferred Structure | Avoid |
|---|---|---|
| Symbol lookup by name | `dict[str, CodeSymbol]` (O(1)) | Linear scan of `list` (O(N)) |
| Membership test | `set` / `frozenset` (O(1)) | `x in list` (O(N)) |
| Graph traversal (impact) | Cached reverse graph / `nx.descendants` | `g.reverse(copy=True)` per call |
| Rename detection | Pre-computed body fingerprints + threshold | Pairwise `SequenceMatcher` (O(D×A×L)) |
| Ordered iteration | `list` / `tuple` | `dict` (unless explicitly requiring insertion order) |
| Frequency counting | `collections.Counter` | Manual dict increment loops |
| Priority-based processing | `heapq` | Repeated `min()` on list |
| Memoization | `functools.lru_cache` / explicit cache dict | Recomputing from scratch |
| File→nodes index | `dict[str, set[NodeID]]` | O(N) scan to find nodes by file |

## 3. GDSS-Specific Patterns
- **Graph Caching**: NetworkX graphs can be expensive to copy. Use view representations or incremental updates rather than deep copies.
- **Incremental AST**: Re-parsing the whole AST is expensive. Prefer extracting updates incrementally if feasible.
- **Embeddings Batching**: When generating embeddings, use batch operations instead of running inference in a loop.

## 4. Anti-Patterns to Avoid
- **Linear membership tests**: Assigning `items = [...]` and checking `if x in items:`. Fix: Use `items = {...}`.
- **Nested loops over same collection**: Checking every item against every other item without a hash map.
- **Graph copy per call**: Calling `.reverse(copy=True)` on a graph within a loop or frequent query path.
- **Dict-building via append+search**: Building a list then searching it to build relationships. Fix: Build a dict directly.
