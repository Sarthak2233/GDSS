# GDSS I/O and Graph Visualization

How data flows through the codebase today, and what you can run from the shell to inspect the dependency graph.

---

## The big picture: data pipeline

<p align="center">
  <img src="../assets/io/pipeline.svg" alt="GDSS I/O pipeline — Git to terminal" width="100%">
</p>

<details>
<summary>🔄 Mermaid source (click to expand)</summary>

```mermaid
flowchart LR
    Git["Git repo<br>commits · files · working tree"]
    GO["GitObserver"]
    AST["ASTParser"]
    TX["TransformExtractor"]
    CG["CodeGraph<br>NetworkX DiGraph"]
    CLI["CLI / Rich terminal"]
    RT["Runtime<br>EventBus + SQLite"]

    Git --> GO
    GO -->|"file content, diffs"| AST
    AST -->|"List[CodeSymbol]"| TX
    AST -->|"List[CodeSymbol]"| CG
    TX -->|"List[SemanticOperator]"| CLI
    TX -->|"op.to_dict()"| RT
    CG -->|"tables, summaries"| CLI
    CG -->|"snapshot"| RT

    style Git fill:#06b6d4,stroke:#035e66,color:#fff
    style GO fill:#0ea5e9,stroke:#075985,color:#fff
    style AST fill:#2563eb,stroke:#1e40af,color:#fff
    style TX fill:#7c3aed,stroke:#4c1d95,color:#fff
    style CG fill:#f59e0b,stroke:#92400e,color:#fff
    style CLI fill:#10b981,stroke:#065f46,color:#fff
    style RT fill:#475569,stroke:#334155,color:#fff
```

</details>

GDSS does **not** persist a graph file or image. The graph lives in memory (`CodeGraph.g`) and is rendered as **Rich tables/trees in the terminal**.

---

## Layer-by-layer I/O

### 1. Git layer — `GitObserver` (`gdss/watcher/git_observer.py`)

| Direction | Type | Description |
|-----------|------|-------------|
| **In** | `repo_path: str` | Path to a Git repo |
| **In** | commit SHAs, branch names | e.g. `"HEAD"`, `"main"`, merge-base |
| **Out** | `get_file_content_at_commit(sha, path) → str` | File text at a historical commit |
| **Out** | `get_file_diffs_between_commits(a, b) → {added, deleted, modified}` | File-level change lists |
| **Out** | `get_working_tree_changes() → {added, deleted, modified}` | Uncommitted/staged changes vs HEAD |
| **Out** | `get_active_branch()`, `get_merge_base()`, etc. | Branch metadata |

This is the **only Git boundary** most of the pipeline uses.

### 2. AST layer — `ASTParser` (`gdss/core/ast_parser.py`)

```python
parse_file(filepath: str, content: Optional[str] = None) -> List[CodeSymbol]
```

| Direction | Detail |
|-----------|--------|
| **In** | File path (and optionally raw source text) |
| **In** | Supported extensions: `.py`, `.js`, `.ts`, `.jsx`, `.tsx` |
| **Out** | `List[CodeSymbol]` — functions, classes, imports, etc. |

Each `CodeSymbol` carries:

- `name`, `type`, `signature`, `body`, `calls`, `body_blocks`
- `structural_tokens` (AST fingerprint for rename detection)
- `symbol_id` (stable ID, position-independent)
- `chart_location` (file path — metadata, not identity)

When `content` is omitted, the parser reads from disk and caches by mtime.

### 3. Transform layer — `TransformExtractor` (`gdss/core/transform_extractor.py`)

```python
extract_operators(file_path, old_symbols, new_symbols, commit_sha="") -> List[SemanticOperator]
```

| Direction | Detail |
|-----------|--------|
| **In** | Two symbol lists (before/after) |
| **In** | `file_path`, optional `commit_sha` |
| **Out** | `List[SemanticOperator]` — add/delete/rename/modify ops |

Each `SemanticOperator` includes:

- `operator` (`OperatorType`), `file`, `name` / `from_name` / `to_name`
- `symbol_id`, `from_symbol_id`, `to_symbol_id`
- `details` (e.g. `changed_blocks` for block-level modifies)
- `to_dict()` for serialization

### 4. Graph layer — `CodeGraph` (`gdss/graph/code_graph.py`)

```python
add_file_symbols(file_path: str, symbols: List[CodeSymbol]) -> None
resolve_calls() -> None
get_downstream_impact(node_id: str) -> Set[str]
get_summary() -> Dict
snapshot() -> Dict  # for tests
```

| Direction | Detail |
|-----------|--------|
| **In** | `CodeSymbol` lists per file |
| **Out** | NetworkX `DiGraph`: nodes `file` / `function` / `class` / import modules |
| **Out** | Node ID = stable `symbol_id` (not `file::name`) |
| **Out** | Edges: `defines`, `calls`, `imports` |
| **Out** | `get_display_id(node_id) → "path/to/file.py::func_name"` |

Operator application lives in `gdss/graph/operator_engine.py`:

```python
apply_operator(op: SemanticOperator, graph: CodeGraph) -> None
invert_operator(op: SemanticOperator) -> SemanticOperator
```

### 5. CLI layer — entry points (`gdss/cli/main.py` → `gdss/cli/start.py`)

| Shell command | What it reads | What it prints |
|---------------|---------------|----------------|
| `gdss start` | Repo path | Interactive shell |
| `gdss status --repo PATH [--ref main]` | merge_base(ref)..HEAD + working tree | Attractor/remote + trajectory operators + uncommitted semantic delta |
| `gdss log -n 5 --repo PATH` | Last N commits | Semantic operators per commit |
| `gdss analyze --repo PATH` | All supported source files | Graph node/edge counts + symbol breakdown |
| `gdss similar SYMBOL --repo PATH [-k 5]` | Symbol embeddings + FAISS/numpy index | Assistive top-k neighbors |
| `gdss reindex --repo PATH` | All supported source files | Rebuild `.gdss/vectors/` |
| `gdss diff TARGET --repo PATH` | Branch diff vs target | File changes + semantic operators |
| `gdss watch --repo PATH` | Event bus | Live monitor panel |
| `gdss graph export --repo PATH -o FILE` | All supported source files | DOT or JSON graph file on disk |

**Interactive-only** (inside `gdss start`):

| Command | Purpose |
|---------|---------|
| `analyze` | Build graph, print summary |
| `impact <symbol>` | Downstream impact table for a symbol name |
| `hierarchy` | Branch priority chain as a Rich tree |
| `log`, `status`, `diff`, `watch` | Same as above |
| `similar <name> [k]` | Assistive embedding neighbors |
| `reindex` | Rebuild local vector index |

---

## End-to-end example: one file change

<p align="center">
  <img src="../assets/io/change_flow.svg" alt="End-to-end flow of a modified file into a semantic operator" width="100%">
</p>

<details>
<summary>🧭 Mermaid source (click to expand)</summary>

```mermaid
flowchart TB
    S1["1 · GitObserver.get_working_tree_changes()<br>→ {'modified': ['utils.py']}"]
    S2["2 · get_file_content_at_commit('HEAD', f) + open(f)<br>→ old_text, new_text"]
    S3["3 · ASTParser.parse_file(f, text) ×2<br>→ old_symbols, new_symbols"]
    S4["4 · TransformExtractor.extract_operators(f, old, new)<br>→ [MODIFY_FUNCTION(changed_blocks=...)]"]
    S5["5 · CLI renders Rich table<br>operator icon · symbol · file"]

    S1 --> S2 --> S3 --> S4 --> S5

    style S1 fill:#0ea5e9,stroke:#075985,color:#fff
    style S2 fill:#0284c7,stroke:#075985,color:#fff
    style S3 fill:#2563eb,stroke:#1e40af,color:#fff
    style S4 fill:#7c3aed,stroke:#4c1d95,color:#fff
    style S5 fill:#10b981,stroke:#065f46,color:#fff
```

</details>

For graph building (`analyze` / `impact`):

```text
walk repo → parse_file(path) → graph.add_file_symbols(path, symbols)
          → graph.resolve_calls()
          → graph.get_summary() or get_downstream_impact(symbol_id)
```

---

## How to visualize the graph from the shell

Built-in terminal views plus first-class graph export.

<p align="center">
  <img src="../assets/io/graph_viz.svg" alt="Ways to visualize the CodeGraph from the shell" width="100%">
</p>

<details>
<summary>🕸️ Mermaid source (click to expand)</summary>

```mermaid
flowchart TD
    CG["CodeGraph.g<br>NetworkX DiGraph (in memory)"]
    A["A · Summary<br>gdss analyze"]
    B["B · Impact<br>impact &lt;symbol&gt;"]
    C["C · Hierarchy<br>hierarchy"]
    D["D · Export<br>gdss graph export"]

    CG --> A
    CG --> B
    CG --> C
    CG --> D

    style CG fill:#f59e0b,stroke:#92400e,color:#fff
    style A fill:#10b981,stroke:#065f46,color:#fff
    style B fill:#2563eb,stroke:#1e40af,color:#fff
    style C fill:#7c3aed,stroke:#4c1d95,color:#fff
    style D fill:#475569,stroke:#334155,color:#fff
```

</details>

### Option A: Summary stats (built-in)

```bash
cd /path/to/your/repo
gdss analyze --repo .
```

Output looks like:

```text
Nodes: 42 | Edges: 87
  • Function: 30
  • Class: 5
  • Import: 7
```

### Option B: Downstream impact (interactive)

```bash
gdss start --repo .
# then at the prompt:
analyze
impact process_payment
```

Prints a table of nodes that **call or depend on** that symbol (via reversed graph traversal).

### Option C: Branch hierarchy tree

```bash
gdss start --repo .
hierarchy
```

### Option D: Export to DOT or JSON (built-in)

```bash
cd /path/to/your/repo

# DOT for Graphviz
gdss graph export --repo . --format dot -o gdss_graph.dot
dot -Tpng gdss_graph.dot -o graph.png   # requires Graphviz installed

# JSON snapshot (nodes + edges)
gdss graph export --repo . --format json -o gdss_graph.json
```

Nodes are labeled with `chart_location::symbol` (via `get_display_id`). Edge labels
carry the relation (`defines`, `calls`, `imports`).

Or inspect in Python:

```python
graph.snapshot()  # {"nodes": {...}, "edges": [(u, v, relation), ...]}
graph.get_summary()
```

---

## What is **not** implemented yet

- No GraphML export format yet (`--format graphml`)
- No web or GUI graph viewer
- No persistent graph database (Neo4j, etc.)
- `impact` is not exposed as `gdss impact ...` — only inside the interactive shell
- Working tree ≠ drift energy: `status` labels WT as **uncommitted semantic delta**; branch drift integral I(B_i) is Phase 3
- `--ref` selects the attractor branch (glossary `dev` is configurable; default often `main`)
- Embeddings (`gdss similar` / FAISS under `.gdss/vectors/`) are **assistive**; continuous drift monitoring is Phase 3
- Optional extras: `pip install -e ".[embeddings]"` for `faiss-cpu` + `onnxruntime` (bag encoder works offline without them)
---

## Quick reference: core data types

| Type | Role | Serialized? |
|------|------|-------------|
| `CodeSymbol` | One AST entity (function, class, …) | `to_dict()` |
| `SemanticOperator` | One semantic change (`dC`) | `to_dict()` |
| `CodeGraph.g` | Live dependency manifold | `snapshot()` (tests only) |
| EventBus payload | `{event, branch, hexsha, semantic_operators: [...]}` | JSON-ish dict to SQLite |

---

