# Multi-Language AST Architecture & .NET Enterprise Support

Type: wayfinder:map
Status: resolved

## Destination

Elevate GDSS to Level 4/5 comprehension for .NET/C# (via official Tree-sitter CST and MSBuild project graph modeling), bundle official Tree-sitter grammars for core tier languages (Ruby, PHP, Bash), and demote naive Tier 3 regex fallback to an explicit, transparent `lexical_advisory` mode.

## Notes

- Domain: Abstract Syntax Trees, Tree-sitter grammars, MSBuild Project Reference DAGs, Semantic Transformation Algebra.
- Skills consulted: `add-semantic-operator`, `tdd`, `domain-modeling`, `codebase-design`.
- Standing preferences: Zero false negatives; never claim semantic comprehension when relying on lexical regex; pure deterministic execution ($0 token cost).

## Decisions so far

- [01: C# Tree-Sitter AST Visitor & CST Mapping](issues/01-csharp-tree-sitter-visitor.md): Implemented native C# AST visitor (`_parse_csharp`) supporting namespaces, classes, interfaces, records, partials, properties, and call invocations.
- [02: Demoting Tier 3 Fallback to Explicit Lexical Advisory](issues/02-tier3-lexical-advisory-demotion.md): Added `has_ast_grammar`/`is_language_supported` checks, transparent warning logs, and `lexical_advisory: true` symbol annotations.
- [03: Core Tree-Sitter Grammar Packaging & Pre-compiled Wheels](issues/03-core-grammar-packaging.md): Added `tree-sitter-c-sharp`, `tree-sitter-ruby`, and `tree-sitter-bash` to `pyproject.toml` with pluggable, lazy loaders.
- [04: Generated Code Exclusion Policy Filter](issues/04-generated-code-exclusion-policy.md): Established `DEFAULT_GENERATED_EXCLUDE_PATTERNS` and `is_generated_or_excluded` across graph builder and trajectory engines.
- [05: MSBuild Project Reference DAG & CPM Manifest Reducer](issues/05-msbuild-project-reference-dag.md): Extended `ManifestReducer` for `.csproj`, `.props`, `.targets`, and CPM with `ADD/REMOVE/MODIFY_DEPENDENCY` operators.
- [06: Hybrid Sub-Document Region Projection Pipeline](issues/06-region-projection-pipeline.md): Implemented `RegionProjector` extracting embedded `@code` from `.razor`/`.cshtml` and `<script>` from `.vue`/`.svelte` with parent coordinate projection.

## Frontier Tickets

*(All frontier tickets resolved.)*

## Blocked Tickets

*(All blocked tickets unblocked and resolved.)*

## Not yet specified

- Roslyn analyzer integration for advanced semantic symbol resolution.
- Dynamic runtime downloading for niche community Tree-sitter grammars (e.g. Solidity, Dart, Lua).
- Fine-grained Blazor HTML markup AST diffing outside `@code` blocks.

## Out of scope

- Direct binary MSBuild execution during AST parsing (must remain pure Python/Tree-sitter on CPU).
- Universal decompilation of compiled `.dll` or `.so` binaries.
