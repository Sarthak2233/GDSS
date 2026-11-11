# 06: Hybrid Sub-Document Region Projection Pipeline

Type: prototype
Status: resolved
Blocked by: 01

## Question

How should GDSS construct a generic `RegionProjector` for hybrid multi-grammar files (`.razor`, `.vue`, `.svelte`)? Specifically, how can it extract isolated code blocks (e.g., `@code { ... }` $\rightarrow$ C#, `<script>` $\rightarrow$ TypeScript/JavaScript) and run them through existing Tree-sitter visitors while accurately projecting inner AST line and column offsets back to original parent document coordinates?

## Answer

1. **Sub-Document Region Projector (`gdss/core/region_projector.py`)**:
   Implemented `RegionProjector` with balanced-brace and tag parsing:
   - **Blazor (`.razor`, `.cshtml`)**: Extracts `@code { ... }` and `@functions { ... }` blocks, wrapping them in a synthetic partial class so `tree-sitter-c-sharp` parses methods, properties, and constructors.
   - **Vue / Svelte (`.vue`, `.svelte`)**: Extracts `<script>` and `<script setup>` tags, detecting `lang="ts"` for TypeScript vs. JavaScript.
2. **Coordinate Projection**:
   Maps extracted inner CST coordinates back to 1-indexed lines and columns of the parent document (`start_line += line_offset`), discarding synthetic wrapper classes and preserving accurate source file locations.
3. **AST Integration (`gdss/core/ast_parser.py`)**:
   Wired into `ASTParser.parse_file` as Tier 0 dispatch for hybrid extensions.
Verified in `tests/core/test_region_projector.py`.
