# 02: Demoting Tier 3 Fallback to Explicit Lexical Advisory

Type: grilling
Status: resolved
Blocked by: none

## Question

How should `gdss.core.ast_parser.ASTParser` and `gdss.core.collision_engine.CollisionRadar` represent files whose extensions lack a registered Tree-sitter grammar? Specifically:
1. Should `parse_file` stop guessing pseudo-symbols via regex and instead return an empty symbol list with a dedicated `lexical_only: true` file metadata flag?
2. How should the PR collision radar sticky report distinguish between true AST symbol collisions ($\Omega_{ij}^{\text{AST}}$) and conservative lexical line overlap ($\Omega_{ij}^{\text{lexical}}$) to eliminate false confidence?

## Answer

Demoted Tier 3 heuristic fallback to explicit lexical advisory mode:
1. **Grammar Authority (`ASTParser.has_ast_grammar(ext)` & `is_language_supported(ext)`)**: Programmatic methods return `True` only for extensions with real Tree-sitter grammars in `LANGUAGE_REGISTRY`.
2. **Transparent Advisory Logging**: If an ungrammared file falls back to `_parse_universal_fallback`, GDSS logs:
   `logger.warning("No Tree-sitter grammar registered for %s (extension %s). Operating in lexical advisory mode.", filepath, ext)`
3. **Symbol Demotion Annotation**: Symbols extracted by the fallback are explicitly tagged with `docstring="lexical_advisory: true"`, signaling to downstream collision sensors and PR report formatters that the boundaries are lexical approximations rather than verified AST nodes.
Verified in `tests/core/test_lexical_fallback_demotion.py`.
