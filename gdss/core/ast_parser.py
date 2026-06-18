import os
from typing import Dict, List, Optional, Tuple, Set
from tree_sitter import Parser, Node, Language
from gdss.core.transform_types import CodeSymbol, SymbolType

class ASTParser:
    """
    AST Parser Engine utilizing Tree-sitter to perform multi-language
    structural parsing for Python, JavaScript, and TypeScript.
    """
    
    def __init__(self):
        self._cache: Dict[str, Tuple[float, List[CodeSymbol]]] = {} # filepath -> (mtime, symbols)

    @staticmethod
    def get_parser_for_ext(ext: str) -> Optional[Parser]:
        try:
            ext_cleaned = ext.lower().strip()
            if ext_cleaned in {".py", "py"}:
                import tree_sitter_python
                lang = Language(tree_sitter_python.language())
            elif ext_cleaned in {".js", "js", ".jsx", "jsx"}:
                import tree_sitter_javascript
                lang = Language(tree_sitter_javascript.language())
            elif ext_cleaned in {".ts", "ts", ".tsx", "tsx"}:
                import tree_sitter_typescript
                lang = Language(tree_sitter_typescript.language())
            else:
                return None
            parser = Parser(lang)
            return parser
        except Exception:
            return None

    def parse_file(self, filepath: str, content: Optional[str] = None) -> List[CodeSymbol]:
        """
        Parses a file path or direct string content and returns a list of extracted CodeSymbols.
        """
        # Check cache if content is not provided
        if content is None:
            if not os.path.exists(filepath):
                return []
            try:
                mtime = os.path.getmtime(filepath)
                if filepath in self._cache:
                    cached_mtime, cached_symbols = self._cache[filepath]
                    if mtime == cached_mtime:
                        return cached_symbols
                
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                return []
        else:
            mtime = None

        ext = os.path.splitext(filepath)[1]
        parser = self.get_parser_for_ext(ext)
        if not parser:
            return []

        try:
            tree = parser.parse(bytes(content, "utf8"))
            root = tree.root_node
        except Exception:
            return []

        symbols: List[CodeSymbol] = []
        
        if ext in {".py", "py"}:
            self._parse_python(root, content, symbols)
        elif ext in {".js", "js", ".jsx", "jsx", ".ts", "ts", ".tsx", "tsx"}:
            self._parse_js_ts(root, content, symbols)

        # Update cache
        if mtime is not None:
            self._cache[filepath] = (mtime, symbols)

        return symbols

    def get_indexed_symbols(self, symbols: List[CodeSymbol]) -> Dict[str, CodeSymbol]:
        """Convert a flat symbol list into an indexed dictionary for O(1) lookups."""
        return {s.name: s for s in symbols}

    def _get_node_text(self, node: Node, content: str) -> str:
        try:
            return content[node.start_byte:node.end_byte]
        except Exception:
            return ""

    def _extract_calls(self, node: Node, content: str, calls: List[str]):
        """Recursively traverses a node to find all function and method call names."""
        if node.type in {"call", "call_expression"}:
            func_node = node.child_by_field_name("function")
            if func_node:
                if func_node.type == "identifier":
                    calls.append(self._get_node_text(func_node, content))
                elif func_node.type == "attribute":  # e.g. obj.method() in Python
                    attr_node = func_node.child_by_field_name("attribute")
                    if attr_node:
                        calls.append(self._get_node_text(attr_node, content))
                elif func_node.type == "member_expression":  # e.g. obj.method() in JS/TS
                    prop_node = func_node.child_by_field_name("property")
                    if prop_node:
                        calls.append(self._get_node_text(prop_node, content))

        for child in node.children:
            self._extract_calls(child, content, calls)

    def _parse_python(self, root: Node, content: str, symbols: List[CodeSymbol], parent_class: Optional[str] = None):
        """Recursively parses a Python AST root node."""
        for child in root.children:
            child_text = self._get_node_text(child, content) # dsa:ignore
            ctype = child.type
            name_node = child.child_by_field_name("name")
            body_node = child.child_by_field_name("body")
            
            name_text = self._get_node_text(name_node, content) if name_node else ""
            body_text = self._get_node_text(body_node, content) if body_node else ""
            
            if ctype == "function_definition":
                if name_node:
                    params_node = child.child_by_field_name("parameters")
                    sig = self._get_node_text(params_node, content) if params_node else "()"
                    
                    # Extract calls inside function body
                    calls = []
                    docstring = None
                    if body_node:
                        self._extract_calls(body_node, content, calls)
                        body_children = body_node.children
                        if body_children:
                            first_stmt = body_children[0]
                            if first_stmt.type == "expression_statement":
                                expr = first_stmt.children[0]
                                if expr.type == "string":
                                    docstring = self._get_node_text(expr, content).strip('"\'')
                    
                    symbols.append(CodeSymbol(
                        name=name_text,
                        type=SymbolType.FUNCTION,
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        signature=sig,
                        body=body_text,
                        docstring=docstring,
                        parent_class=parent_class,
                        calls=calls
                    ))
            
            elif ctype == "class_definition":
                if name_node:
                    # Extract superclasses for signature
                    super_node = child.child_by_field_name("superclasses")
                    sig = self._get_node_text(super_node, content) if super_node else ""

                    symbols.append(CodeSymbol(
                        name=name_text,
                        type=SymbolType.CLASS,
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        signature=sig,
                        body=body_text,
                        parent_class=parent_class
                    ))
                    
                    # Parse functions inside the class body
                    if body_node:
                        self._parse_python(body_node, content, symbols, parent_class=name_text)

            elif ctype == "assignment":
                # Top-level variables or constants
                if parent_class is None: # Only at module level for now
                    left_node = child.child_by_field_name("left")
                    if left_node and left_node.type == "identifier":
                        name = self._get_node_text(left_node, content)
                        # Heuristic: ALL_CAPS = Constant
                        stype = SymbolType.CONSTANT if name.isupper() else SymbolType.VARIABLE
                        
                        symbols.append(CodeSymbol(
                            name=name,
                            type=stype,
                            start_line=child.start_point[0] + 1,
                            end_line=child.end_point[0] + 1,
                            signature=name,
                            body=child_text
                        ))

            if ctype == "import_statement":
                # Use cached child_text
                text = child_text
                # Simple parsing: 'import os, sys'
                parts = text.replace("import", "").strip().split(",")
                for p in parts:
                    iname = p.strip().split(" as ")[0].strip()
                    symbols.append(CodeSymbol(
                        name=iname,
                        type=SymbolType.IMPORT,
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        module=iname
                    ))

            elif ctype == "import_from_statement":
                # 'from math import sin, cos'
                # Use child_text for the whole node if needed for parsing, but here we just need to re-parse sub-children
                # Actually, the parser logic here does not use child_text, so this is fine.
                dotted_nodes = [sub for sub in child.children if sub.type == "dotted_name"]

                if dotted_nodes:
                    module_name = self._get_node_text(dotted_nodes[0], content)
                    imported_names = []
                    
                    # Find if there is an 'import' keyword index
                    import_keyword_idx = -1
                    for idx, sub in enumerate(child.children):
                        if sub.type == "import":
                            import_keyword_idx = idx
                            break
                    
                    if import_keyword_idx != -1:
                        for sub in child.children[import_keyword_idx + 1:]:
                            stype = sub.type
                            if stype == "dotted_name":
                                imported_names.append(self._get_node_text(sub, content))
                            elif stype == "aliased_import":
                                sub_names = [self._get_node_text(n, content) for n in sub.children if n.type in {"identifier", "dotted_name"}]
                                if sub_names:
                                    imported_names.append(sub_names[0])
                            elif stype == "wildcard_import":
                                imported_names.append("*")

                    symbols.append(CodeSymbol(
                        name=module_name,
                        type=SymbolType.IMPORT,
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        module=module_name,
                        imported_names=imported_names
                    ))
            
            else:
                # Recurse for general containers (e.g. if statements, try/except block, etc. - unless already handled)
                if ctype not in {"function_definition", "class_definition", "import_statement", "import_from_statement"} and child.children:
                    self._parse_python(child, content, symbols, parent_class)

    def _parse_js_ts(self, root: Node, content: str, symbols: List[CodeSymbol], parent_class: Optional[str] = None):
        """Recursively parses a Javascript/Typescript AST root node."""
        for child in root.children:
            child_text = self._get_node_text(child, content) # dsa:ignore
            ctype = child.type
            name_node = child.child_by_field_name("name")
            body_node = child.child_by_field_name("body")
            
            # DSA: cache text extraction to avoid repeated calls across branches
            name_text = self._get_node_text(name_node, content) if name_node else ""
            body_text = self._get_node_text(body_node, content) if body_node else ""
            
            if ctype in {"function_declaration", "method_definition"}:
                if name_node:
                    params_node = child.child_by_field_name("parameters")
                    sig = self._get_node_text(params_node, content) if params_node else "()"
                    
                    # Extract calls inside function body
                    calls = []
                    if body_node:
                        self._extract_calls(body_node, content, calls)

                    symbols.append(CodeSymbol(
                        name=name_text,
                        type=SymbolType.FUNCTION,
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        signature=sig,
                        body=body_text,
                        parent_class=parent_class,
                        calls=calls
                    ))
            
            elif ctype == "class_declaration":
                if name_node:
                    # Inheritance
                    heritage_node = child.child_by_field_name("heritage")
                    sig = self._get_node_text(heritage_node, content) if heritage_node else ""

                    symbols.append(CodeSymbol(
                        name=name_text,
                        type=SymbolType.CLASS,
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        signature=sig,
                        body=body_text,
                        parent_class=parent_class
                    ))
                    
                    if body_node:
                        self._parse_js_ts(body_node, content, symbols, parent_class=name_text)

            elif ctype == "import_statement":
                # 'import { foo, bar } from "mod"' or 'import defaultExport from "mod"'
                source_node = next((c for c in child.children if c.type == "string"), None)
                module_name = self._get_node_text(source_node, content).strip("'\"") if source_node else ""
                
                imported_names = []
                clause = next((c for c in child.children if c.type == "import_clause"), None)
                if clause:
                    # check for named imports
                    named = next((c for c in clause.children if c.type == "named_imports"), None)
                    if named:
                        for spec in named.children:
                            if spec.type == "import_specifier":
                                # Extract original name or alias
                                sname_node = spec.child_by_field_name("name")
                                if sname_node:
                                    imported_names.append(self._get_node_text(sname_node, content))
                                else:
                                    id_nodes = [n for n in spec.children if n.type == "identifier"]
                                    if id_nodes:
                                        imported_names.append(self._get_node_text(id_nodes[0], content))
                    
                    # check for namespace import (e.g. * as utils)
                    namespace = next((c for c in clause.children if c.type == "namespace_import"), None)
                    if namespace:
                        id_nodes = [n for n in namespace.children if n.type == "identifier"]
                        if id_nodes:
                            imported_names.append(self._get_node_text(id_nodes[0], content))

                    # check for default identifier import
                    default_id = next((c for c in clause.children if c.type == "identifier"), None)
                    if default_id:
                        imported_names.append(self._get_node_text(default_id, content))

                symbols.append(CodeSymbol(
                    name=module_name,
                    type=SymbolType.IMPORT,
                    start_line=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    module=module_name,
                    imported_names=imported_names
                ))
            
            else:
                if ctype not in {"function_declaration", "method_definition", "class_declaration", "import_statement"} and child.children:
                    self._parse_js_ts(child, content, symbols, parent_class)
