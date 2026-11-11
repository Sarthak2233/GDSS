# Domain Glossary: GDSS Multi-Language & Semantic Grammar Architecture

This glossary defines standard terminology for GDSS's multi-language parsing, grammar tiers, and project dependency topology.

---

### Language Comprehension Level
A 5-level hierarchy measuring the depth of repository analysis for any given programming language:
* **Level 1 (Extension Matching):** Recognizing a file extension as source code without semantic verification.
* **Level 2 (Concrete Syntax Tree):** Lossless AST generation using an official Tree-sitter grammar.
* **Level 3 (Scoped Symbol Extraction):** Structural extraction of namespaces, classes, interfaces, methods, properties, and parameters.
* **Level 4 (Cross-Project Topology):** Resolving build manifests (`.csproj`, `Cargo.toml`, `package.json`), project references, and package dependencies into a directed acyclic graph (DAG).
* **Level 5 (Transformation Algebra):** Calculating non-commutative operations, contract violations, and pairwise collision intensity ($\Omega_{ij}$).

### Lexical Advisory Mode
A transparent safety-net mode for languages or file types without a registered Tree-sitter grammar. Emits a file-level overlap advisory without attempting regex-based symbol or method extraction, preventing false negatives.

### Region Projection
The technique of extracting embedded code segments from composite documents (such as `@code { ... }` in `.razor` or `<script>` in `.vue`) and routing them to their respective parent language AST parsers with offset preservation.

### Project Reference DAG
A directed graph of inter-project dependencies parsed from build system manifests (e.g. MSBuild `<ProjectReference>` tags, Cargo workspace members, npm workspace packages).

### Generated Code Exclusion Policy
A deterministic filter identifying auto-generated files (e.g. `*.g.cs`, `*.Designer.cs`, `*.pb.go`) to prevent compiler artifacts from distorting collision metrics.

