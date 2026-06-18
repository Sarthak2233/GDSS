# DSA Optimization Skill

When you write performance-sensitive code, or are asked to optimize an existing module, invoke this skill to ensure algorithmic efficiency.

## The Workflow

1. **PROFILE**: Identify the hot path and current theoretical complexity. What is O(N) where N could be large?
2. **SELECT**: Choose the optimal data structure from the DSA selection matrix (see `35-dsa-optimization.mdc`).
3. **IMPLEMENT**: Write the optimized version. Add complexity annotations or comments for non-trivial algorithms.
4. **BENCHMARK** (Optional): If possible, run a small test to confirm improvements (e.g. using `timeit`).
5. **DOCUMENT**: Add a docstring noting the complexity choice and rationale.

## GDSS DSA Cheat Sheet (Per Layer)

- **Layer 2 (Watcher)**
  - Cache diff outputs if querying the same commit repeatedly.
  - Process commits in batches to avoid GitPython iteration overhead.
- **Layer 3-4 (Core)**
  - **Symbol Indexing**: Avoid flat `List[CodeSymbol]`. Maintain an inverted index: `dict[str, CodeSymbol]`.
  - Dedup transforms via hashes, not pairwise comparison.
- **Layer 5 (Graph)**
  - Avoid `g.reverse(copy=True)` in a hot loop. Use `nx.DiGraph.reverse(copy=False)` which returns a view.
  - Maintain a mapping of `File -> Set[NodeID]` to prevent O(N) scans when adding/removing symbols.
- **Layer 6 (Embeddings)**
  - Vector operations must be vectorized (numpy/torch/ONNX batch ops). Never run inference inside a python `for` loop.
  - Use `functools.lru_cache` for embeddings of unchanged symbols.
- **Layer 7-8 (Conflict/Drift)**
  - Tensors ($\Omega_{ij}$) are likely sparse. Do not allocate dense N×N matrices if N is large. Use sparse representations (dict of dicts or scipy sparse).
