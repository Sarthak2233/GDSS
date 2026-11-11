# 01: C# Tree-Sitter AST Visitor & CST Mapping

Type: research
Status: resolved
Blocked by: none

## Question

How does `tree-sitter-c-sharp` represent core C# language constructs (namespaces, classes, interfaces, records, partial types, generic constraints, properties with `init`/`required`, expression-bodied members, and async methods) in its Concrete Syntax Tree, and how should GDSS's `ASTParser._parse_csharp` visitor extract them into `CodeSymbol` records with accurate signatures, parents, and location coordinates?

## Answer

`tree-sitter-c-sharp` (v0.23.5+) provides complete CST nodes for modern C# 10/11/12 constructs.
Implemented in `gdss/core/ast_parser.py::_parse_csharp`:
1. **Namespaces**: Supports block-scoped (`namespace_declaration`) and C# 10+ file-scoped (`file_scoped_namespace_declaration`) namespaces, maintaining hierarchical parent naming for all enclosing types.
2. **Types**: Extracts `class_declaration`, `interface_declaration`, `record_declaration`, `record_struct_declaration`, `struct_declaration`, and `enum_declaration` into `SymbolType.CLASS`. Accurately preserves generic parameters (`type_parameter_list`, e.g. `<T>`) and base class/interface hierarchies (`base_list`).
3. **Members**: Extracts `method_declaration`, `constructor_declaration`, and `destructor_declaration` into `SymbolType.FUNCTION`.
4. **Properties**: Extracts `property_declaration` (`required`, `init`, expression-bodied `=>`) and `indexer_declaration` into `SymbolType.FUNCTION`.
5. **Calls**: Extracts caller/callee dependencies from `invocation_expression` and `member_access_expression` directly into `sym.calls`.
6. **Imports**: Extracts `using_directive` into `SymbolType.IMPORT`.
Verified with 100% pass rate in `tests/core/test_csharp_tree_sitter.py`.
