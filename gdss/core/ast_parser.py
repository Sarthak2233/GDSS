import hashlib
import os
from collections import OrderedDict
from collections.abc import Callable

from tree_sitter import Language, Node, Parser

from gdss.core.structural_fingerprint import extract_tokens_from_body_text
from gdss.core.transform_types import BodyBlock, CodeSymbol, SymbolType


# Pluggable Tree-sitter grammar registry: ext -> (language_name, import_loader)
def _load_python():
    import tree_sitter_python
    return Language(tree_sitter_python.language())


def _load_javascript():
    import tree_sitter_javascript
    return Language(tree_sitter_javascript.language())


def _load_typescript():
    import tree_sitter_typescript
    return Language(tree_sitter_typescript.language_typescript())


def _load_tsx():
    import tree_sitter_typescript
    return Language(tree_sitter_typescript.language_tsx())


def _load_go():
    import tree_sitter_go
    return Language(tree_sitter_go.language())


LANGUAGE_REGISTRY: dict[str, tuple[str, Callable[[], Language]]] = {
    ".py": ("python", _load_python),
    ".js": ("javascript", _load_javascript),
    ".jsx": ("javascript", _load_javascript),
    ".ts": ("typescript", _load_typescript),
    ".tsx": ("typescript", _load_tsx),
    ".go": ("go", _load_go),
}

SOURCE_EXTENSIONS: tuple[str, ...] = tuple(LANGUAGE_REGISTRY.keys())

_CONTENT_CACHE_MAX = 256


class ASTParser:
    """
    AST Parser Engine utilizing Tree-sitter to perform multi-language
    structural parsing for Python, JavaScript, TypeScript, and Go.
    """

    def __init__(self, content_cache_max: int = _CONTENT_CACHE_MAX):
        # filepath -> (mtime, symbols)
        self._cache: dict[str, tuple[float, list[CodeSymbol]]] = {}
        # content_hash -> symbols (LRU)
        self._content_cache: OrderedDict[str, list[CodeSymbol]] = OrderedDict()
        self._content_cache_max = content_cache_max
        self._skipped_extensions: dict[str, int] = {}

    @staticmethod
    def get_parser_for_ext(ext: str) -> Parser | None:
        try:
            ext_cleaned = ext.lower().strip()
            if not ext_cleaned.startswith("."):
                ext_cleaned = f".{ext_cleaned}"
            entry = LANGUAGE_REGISTRY.get(ext_cleaned)
            if not entry:
                return None
            _lang_name, loader = entry
            parser = Parser(loader())
            return parser
        except Exception:
            return None

    def consume_skipped_summary(self) -> dict[str, int]:
        """Return and clear counts of files skipped due to missing parsers."""
        summary = dict(self._skipped_extensions)
        self._skipped_extensions.clear()
        return summary

    def _remember_content(self, cache_key: str, symbols: list[CodeSymbol]) -> None:
        self._content_cache[cache_key] = symbols
        self._content_cache.move_to_end(cache_key)
        while len(self._content_cache) > self._content_cache_max:
            self._content_cache.popitem(last=False)

    def parse_file(self, filepath: str, content: str | None = None) -> list[CodeSymbol]:
        """
        Parses a file path or direct string content and returns a list of extracted CodeSymbols.
        """
        mtime: float | None = None
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

                with open(filepath, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                return []

        content_bytes = content.encode("utf-8")
        content_hash = hashlib.sha256(content_bytes).hexdigest()
        cache_key = f"{filepath}:{content_hash}"
        if cache_key in self._content_cache:
            self._content_cache.move_to_end(cache_key)
            cached = self._content_cache[cache_key]
            if mtime is not None:
                self._cache[filepath] = (mtime, cached)
            return cached

        ext = os.path.splitext(filepath)[1].lower()
        language = self._language_for_ext(ext)
        parser = self.get_parser_for_ext(ext)
        if not parser:
            if ext:
                self._skipped_extensions[ext] = self._skipped_extensions.get(ext, 0) + 1
            return []

        try:
            tree = parser.parse(content_bytes)
            root = tree.root_node
        except Exception:
            return []

        symbols: list[CodeSymbol] = []

        if language == "python":
            self._parse_python(root, content_bytes, symbols, language=language, chart_location=filepath)
        elif language in {"javascript", "typescript"}:
            self._parse_js_ts(root, content_bytes, symbols, language=language, chart_location=filepath)
        elif language == "go":
            self._parse_go(root, content_bytes, symbols, language=language, chart_location=filepath)

        if mtime is not None:
            self._cache[filepath] = (mtime, symbols)
        self._remember_content(cache_key, symbols)

        return symbols

    def get_indexed_symbols(self, symbols: list[CodeSymbol]) -> dict[tuple[str, str], CodeSymbol]:
        """Index symbols by (parent_class, name) for O(1) lookups without collisions."""
        return {(s.parent_class or "", s.name): s for s in symbols}

    def _get_node_text(self, node: Node, content_bytes: bytes) -> str:
        """Decode node text using Tree-sitter byte offsets (not Python str indices)."""
        try:
            return content_bytes[node.start_byte:node.end_byte].decode("utf-8")
        except Exception:
            return ""

    @staticmethod
    def _language_for_ext(ext: str) -> str:
        cleaned = ext.lower().strip()
        if not cleaned.startswith("."):
            cleaned = f".{cleaned}"
        entry = LANGUAGE_REGISTRY.get(cleaned)
        return entry[0] if entry else "unknown"

    def _extract_structural_tokens(self, node: Node | None) -> list[str]:
        if not node:
            return []
        tokens: list[str] = []
        for child in node.children:
            if child.is_named:
                tokens.append(child.type)
        return tokens

    def _extract_body_blocks(self, body_node: Node | None, content_bytes: bytes) -> list[BodyBlock]:
        if not body_node:
            return []
        blocks: list[BodyBlock] = []
        counters: dict[str, int] = {}
        for child in body_node.children:
            if not child.is_named:
                continue
            count = counters.get(child.type, 0)
            block_id = f"{child.type}_{count}"
            counters[child.type] = count + 1
            block_tokens = self._extract_structural_tokens(child)
            blocks.append(
                BodyBlock(
                    block_id=block_id,
                    node_type=child.type,
                    start_line=child.start_point[0] + 1,
                    end_line=child.end_point[0] + 1,
                    structural_tokens=block_tokens or [child.type],
                )
            )
        return blocks

    def _extract_calls(self, node: Node, content_bytes: bytes, calls: list[str]):
        """Recursively traverses a node to find all function and method call names."""
        if node.type in {"call", "call_expression"}:
            func_node = node.child_by_field_name("function")
            if func_node:
                if func_node.type == "identifier":
                    calls.append(self._get_node_text(func_node, content_bytes))
                elif func_node.type == "attribute":  # e.g. obj.method() in Python
                    attr_node = func_node.child_by_field_name("attribute")
                    if attr_node:
                        calls.append(self._get_node_text(attr_node, content_bytes))
                elif func_node.type == "member_expression":  # e.g. obj.method() in JS/TS
                    prop_node = func_node.child_by_field_name("property")
                    if prop_node:
                        calls.append(self._get_node_text(prop_node, content_bytes))

        for child in node.children:
            self._extract_calls(child, content_bytes, calls)

    def _append_symbol(
        self,
        symbols: list[CodeSymbol],
        sym: CodeSymbol,
        chart_location: str | None,
    ) -> None:
        sym.ensure_identity(chart_location)
        symbols.append(sym)

    def _parse_python(
        self,
        root: Node,
        content_bytes: bytes,
        symbols: list[CodeSymbol],
        parent_class: str | None = None,
        language: str = "python",
        chart_location: str | None = None,
    ):
        """Recursively parses a Python AST root node."""
        for child in root.children:
            child_text = self._get_node_text(child, content_bytes)  # dsa:ignore
            ctype = child.type
            name_node = child.child_by_field_name("name")
            body_node = child.child_by_field_name("body")

            name_text = self._get_node_text(name_node, content_bytes) if name_node else ""
            body_text = self._get_node_text(body_node, content_bytes) if body_node else ""

            if ctype == "function_definition":
                if name_node:
                    params_node = child.child_by_field_name("parameters")
                    sig = self._get_node_text(params_node, content_bytes) if params_node else "()"

                    # Extract calls inside function body
                    calls: list[str] = []
                    docstring = None
                    if body_node:
                        self._extract_calls(body_node, content_bytes, calls)
                        body_children = body_node.children
                        if body_children:
                            first_stmt = body_children[0]
                            if first_stmt.type == "expression_statement":
                                expr = first_stmt.children[0]
                                if expr.type == "string":
                                    docstring = self._get_node_text(expr, content_bytes).strip('"\'')

                    body_blocks = self._extract_body_blocks(body_node, content_bytes)
                    structural_tokens = (
                        [b.node_type for b in body_blocks]
                        if body_blocks
                        else extract_tokens_from_body_text(body_text)
                    )
                    sym = CodeSymbol(
                        name=name_text,
                        type=SymbolType.FUNCTION,
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        signature=sig,
                        body=body_text,
                        docstring=docstring,
                        parent_class=parent_class,
                        calls=calls,
                        structural_tokens=structural_tokens,
                        body_blocks=body_blocks,
                        language=language,
                        chart_location=chart_location,
                    )
                    self._append_symbol(symbols, sym, chart_location)  # dsa:ignore per-symbol registration

            elif ctype == "class_definition":
                if name_node:
                    # Extract superclasses for signature
                    super_node = child.child_by_field_name("superclasses")
                    sig = self._get_node_text(super_node, content_bytes) if super_node else ""

                    sym = CodeSymbol(
                        name=name_text,
                        type=SymbolType.CLASS,
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        signature=sig,
                        body=body_text,
                        parent_class=parent_class,
                        structural_tokens=self._extract_structural_tokens(body_node),
                        language=language,
                        chart_location=chart_location,
                    )
                    self._append_symbol(symbols, sym, chart_location)  # dsa:ignore per-symbol registration

                    if body_node:
                        self._parse_python(
                            body_node,
                            content_bytes,
                            symbols,
                            parent_class=name_text,
                            language=language,
                            chart_location=chart_location,
                        )

            elif ctype == "assignment":
                # Top-level variables or constants
                if parent_class is None: # Only at module level for now
                    left_node = child.child_by_field_name("left")
                    if left_node and left_node.type == "identifier":
                        name = self._get_node_text(left_node, content_bytes)
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
                    module_name = self._get_node_text(dotted_nodes[0], content_bytes)
                    imported_names = []

                    # Find if there is an 'import' keyword index
                    import_keyword_idx = -1
                    for idx, sub in enumerate(child.children):
                        if sub.type == "import":
                            import_keyword_idx = idx
                            break

                    if import_keyword_idx != -1:
                        for sub in child.children[import_keyword_idx + 1:]:
                            sub_type = sub.type
                            if sub_type == "dotted_name":
                                imported_names.append(self._get_node_text(sub, content_bytes))
                            elif sub_type == "aliased_import":
                                sub_names = [self._get_node_text(n, content_bytes) for n in sub.children if n.type in {"identifier", "dotted_name"}]
                                if sub_names:
                                    imported_names.append(sub_names[0])
                            elif sub_type == "wildcard_import":
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
                    self._parse_python(
                        child,
                        content_bytes,
                        symbols,
                        parent_class,
                        language=language,
                        chart_location=chart_location,
                    )

    def _parse_js_ts(
        self,
        root: Node,
        content_bytes: bytes,
        symbols: list[CodeSymbol],
        parent_class: str | None = None,
        language: str = "javascript",
        chart_location: str | None = None,
    ):
        """Recursively parses a Javascript/Typescript AST root node."""
        for child in root.children:
            ctype = child.type
            name_node = child.child_by_field_name("name")
            body_node = child.child_by_field_name("body")

            # DSA: cache text extraction to avoid repeated calls across branches
            name_text = self._get_node_text(name_node, content_bytes) if name_node else ""
            body_text = self._get_node_text(body_node, content_bytes) if body_node else ""

            if ctype in {"function_declaration", "method_definition"}:
                if name_node:
                    params_node = child.child_by_field_name("parameters")
                    sig = self._get_node_text(params_node, content_bytes) if params_node else "()"

                    # Extract calls inside function body
                    calls: list[str] = []
                    if body_node:
                        self._extract_calls(body_node, content_bytes, calls)

                    body_blocks = self._extract_body_blocks(body_node, content_bytes)
                    structural_tokens = (
                        [b.node_type for b in body_blocks]
                        if body_blocks
                        else extract_tokens_from_body_text(body_text)
                    )
                    sym = CodeSymbol(
                        name=name_text,
                        type=SymbolType.FUNCTION,
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        signature=sig,
                        body=body_text,
                        parent_class=parent_class,
                        calls=calls,
                        structural_tokens=structural_tokens,
                        body_blocks=body_blocks,
                        language=language,
                        chart_location=chart_location,
                    )
                    self._append_symbol(symbols, sym, chart_location)  # dsa:ignore per-symbol registration

            elif ctype == "class_declaration":
                if name_node:
                    # Inheritance
                    heritage_node = child.child_by_field_name("heritage")
                    sig = self._get_node_text(heritage_node, content_bytes) if heritage_node else ""

                    sym = CodeSymbol(
                        name=name_text,
                        type=SymbolType.CLASS,
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        signature=sig,
                        body=body_text,
                        parent_class=parent_class,
                        structural_tokens=self._extract_structural_tokens(body_node),
                        language=language,
                        chart_location=chart_location,
                    )
                    self._append_symbol(symbols, sym, chart_location)  # dsa:ignore per-symbol registration

                    if body_node:
                        self._parse_js_ts(
                            body_node,
                            content_bytes,
                            symbols,
                            parent_class=name_text,
                            language=language,
                            chart_location=chart_location,
                        )

            elif ctype == "import_statement":
                # 'import { foo, bar } from "mod"' or 'import defaultExport from "mod"'
                source_node = next((c for c in child.children if c.type == "string"), None)
                module_name = self._get_node_text(source_node, content_bytes).strip("'\"") if source_node else ""

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
                                    imported_names.append(self._get_node_text(sname_node, content_bytes))
                                else:
                                    id_nodes = [n for n in spec.children if n.type == "identifier"]
                                    if id_nodes:
                                        imported_names.append(self._get_node_text(id_nodes[0], content_bytes))

                    # check for namespace import (e.g. * as utils)
                    namespace = next((c for c in clause.children if c.type == "namespace_import"), None)
                    if namespace:
                        id_nodes = [n for n in namespace.children if n.type == "identifier"]
                        if id_nodes:
                            imported_names.append(self._get_node_text(id_nodes[0], content_bytes))

                    # check for default identifier import
                    default_id = next((c for c in clause.children if c.type == "identifier"), None)
                    if default_id:
                        imported_names.append(self._get_node_text(default_id, content_bytes))

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
                    self._parse_js_ts(
                        child,
                        content_bytes,
                        symbols,
                        parent_class,
                        language=language,
                        chart_location=chart_location,
                    )

    def _parse_go(
        self,
        root: Node,
        content_bytes: bytes,
        symbols: list[CodeSymbol],
        parent_class: str | None = None,
        language: str = "go",
        chart_location: str | None = None,
    ):
        """Recursively parse Go AST nodes (functions, methods, types)."""
        for child in root.children:
            ctype = child.type
            name_node = child.child_by_field_name("name")
            body_node = child.child_by_field_name("body")
            name_text = self._get_node_text(name_node, content_bytes) if name_node else ""
            body_text = self._get_node_text(body_node, content_bytes) if body_node else ""

            if ctype in {"function_declaration", "method_declaration"}:
                if name_node:
                    params_node = child.child_by_field_name("parameters")
                    sig = self._get_node_text(params_node, content_bytes) if params_node else "()"
                    calls: list[str] = []
                    if body_node:
                        self._extract_calls(body_node, content_bytes, calls)
                    body_blocks = self._extract_body_blocks(body_node, content_bytes)
                    structural_tokens = (
                        [b.node_type for b in body_blocks]
                        if body_blocks
                        else extract_tokens_from_body_text(body_text)
                    )
                    recv = child.child_by_field_name("receiver")
                    parent = parent_class
                    if recv is not None and parent is None:
                        recv_text = self._get_node_text(recv, content_bytes)
                        parent = recv_text.strip("()") or parent_class
                    sym = CodeSymbol(
                        name=name_text,
                        type=SymbolType.FUNCTION,
                        start_line=child.start_point[0] + 1,
                        end_line=child.end_point[0] + 1,
                        signature=sig,
                        body=body_text,
                        parent_class=parent,
                        calls=calls,
                        structural_tokens=structural_tokens,
                        body_blocks=body_blocks,
                        language=language,
                        chart_location=chart_location,
                    )
                    self._append_symbol(symbols, sym, chart_location)  # dsa:ignore

            elif ctype == "type_declaration":
                for spec in child.children:
                    if spec.type != "type_spec":
                        continue
                    tname = spec.child_by_field_name("name")
                    if not tname:
                        continue
                    tname_text = self._get_node_text(tname, content_bytes)
                    type_node = spec.child_by_field_name("type")
                    type_text = self._get_node_text(type_node, content_bytes) if type_node else ""
                    stype = (
                        SymbolType.CLASS
                        if (type_node and type_node.type == "struct_type")
                        else SymbolType.VARIABLE
                    )
                    sym = CodeSymbol(
                        name=tname_text,
                        type=stype,
                        start_line=spec.start_point[0] + 1,
                        end_line=spec.end_point[0] + 1,
                        signature=type_text[:80],
                        body=type_text,
                        language=language,
                        chart_location=chart_location,
                    )
                    self._append_symbol(symbols, sym, chart_location)  # dsa:ignore

            elif child.children and ctype not in {
                "function_declaration",
                "method_declaration",
                "type_declaration",
            }:
                self._parse_go(
                    child,
                    content_bytes,
                    symbols,
                    parent_class,
                    language=language,
                    chart_location=chart_location,
                )
