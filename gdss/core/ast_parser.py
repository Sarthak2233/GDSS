import hashlib
import os
import re
from collections import OrderedDict
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypedDict

from tree_sitter import Language, Node, Parser

from gdss.core.structural_fingerprint import extract_tokens_from_body_text
from gdss.core.transform_types import BodyBlock, CodeSymbol, SymbolType
from gdss.logger import get_logger

logger = get_logger("gdss.core.ast_parser")


class LocationKwargs(TypedDict):
    start_line: int
    end_line: int
    start_column: int
    end_column: int


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


def _load_rust():
    import tree_sitter_rust

    return Language(tree_sitter_rust.language())


def _load_java():
    import tree_sitter_java

    return Language(tree_sitter_java.language())


def _load_c():
    import tree_sitter_c

    return Language(tree_sitter_c.language())


def _load_cpp():
    import tree_sitter_cpp

    return Language(tree_sitter_cpp.language())


LANGUAGE_REGISTRY: dict[str, tuple[str, Callable[[], Language | None]]] = {
    ".py": ("python", _load_python),
    ".pyi": ("python", _load_python),
    ".js": ("javascript", _load_javascript),
    ".jsx": ("javascript", _load_javascript),
    ".mjs": ("javascript", _load_javascript),
    ".cjs": ("javascript", _load_javascript),
    ".ts": ("typescript", _load_typescript),
    ".tsx": ("typescript", _load_tsx),
    ".go": ("go", _load_go),
    ".rs": ("rust", _load_rust),
    ".java": ("java", _load_java),
    ".c": ("c", _load_c),
    ".h": ("c", _load_c),
    ".cpp": ("cpp", _load_cpp),
    ".hpp": ("cpp", _load_cpp),
    ".cc": ("cpp", _load_cpp),
    ".cxx": ("cpp", _load_cpp),
}

DEFAULT_SOURCE_EXTENSIONS: tuple[str, ...] = (
    ".py",
    ".pyi",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cc",
    ".cxx",
    ".cs",
    ".rb",
    ".php",
    ".kt",
    ".kts",
    ".swift",
    ".scala",
    ".sh",
    ".bash",
    ".zsh",
    ".dart",
    ".lua",
    ".sol",
)

SOURCE_EXTENSIONS: tuple[str, ...] = DEFAULT_SOURCE_EXTENSIONS


def get_source_extensions(repo_root: Path | str | None = None) -> tuple[str, ...]:
    """Return all source extensions tracked by GDSS, merged with any .gdss.yml config."""
    custom_exts: list[str] = []
    if repo_root is not None:
        p = Path(repo_root)
        config_file = p / ".gdss.yml"
        has_config = config_file.is_file()
        if not has_config:
            config_file = p / ".gdss.yaml"
            has_config = config_file.is_file()  # dsa:ignore
        if has_config:
            try:
                import yaml

                data = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
                ast_cfg = data.get("ast", {})
                if isinstance(ast_cfg, dict):
                    raw_exts = ast_cfg.get("additional_extensions", [])
                    if isinstance(raw_exts, list):
                        for e in raw_exts:
                            e_norm = str(e).lower().strip()
                            if e_norm and not e_norm.startswith("."):
                                e_norm = f".{e_norm}"
                            if e_norm:
                                custom_exts.append(e_norm)
            except Exception:
                pass

    all_exts = list(DEFAULT_SOURCE_EXTENSIONS) + list(LANGUAGE_REGISTRY.keys()) + custom_exts
    seen: set[str] = set()
    result: list[str] = []
    for ext in all_exts:
        if ext not in seen:
            seen.add(ext)
            result.append(ext)
    return tuple(result)


_CONTENT_CACHE_MAX = 256


class ASTParser:
    """
    AST Parser Engine utilizing Tree-sitter and Universal Fallback to perform
    multi-language structural parsing across any repository.
    """

    _CUSTOM_VISITORS: dict[
        str,
        Callable[..., None],
    ] = {}

    @classmethod
    def register_language(
        cls,
        ext: str,
        language_name: str,
        loader: Callable[[], Language] | None = None,
        visitor: Callable[..., None] | None = None,
    ) -> None:
        """Register a new language extension dynamically with optional Tree-sitter loader and custom visitor."""
        ext_norm = ext.lower().strip()
        if not ext_norm.startswith("."):
            ext_norm = f".{ext_norm}"

        if loader is not None:
            LANGUAGE_REGISTRY[ext_norm] = (language_name, loader)
        else:
            LANGUAGE_REGISTRY[ext_norm] = (language_name, lambda: None)

        if visitor is not None:
            cls._CUSTOM_VISITORS[language_name] = visitor

        global DEFAULT_SOURCE_EXTENSIONS, SOURCE_EXTENSIONS
        all_exts_set = set(DEFAULT_SOURCE_EXTENSIONS)
        if ext_norm not in all_exts_set:
            DEFAULT_SOURCE_EXTENSIONS = DEFAULT_SOURCE_EXTENSIONS + (ext_norm,)
            SOURCE_EXTENSIONS = DEFAULT_SOURCE_EXTENSIONS

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
            loaded = loader()
            if not loaded:
                return None
            parser = Parser(loaded)
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
        Uses 3-tier parsing:
        - Tier 1: Specialized Tree-sitter AST visitor (Python, JS/TS, Go, Rust, Java, C/C++)
        - Tier 2: Universal Tree-sitter Node Walker (any registered Tree-sitter grammar)
        - Tier 3: Universal Structural Block Fallback (never skips, 100% coverage)
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
        symbols: list[CodeSymbol] = []

        custom_visitor = self._CUSTOM_VISITORS.get(language)

        if parser:
            try:
                tree = parser.parse(content_bytes)
                root = tree.root_node
                if custom_visitor:
                    custom_visitor(
                        self,
                        root,
                        content_bytes,
                        symbols,
                        parent_class=None,
                        language=language,
                        chart_location=filepath,
                    )
                elif language == "python":
                    self._parse_python(
                        root, content_bytes, symbols, language=language, chart_location=filepath
                    )
                elif language in {"javascript", "typescript"}:
                    self._parse_js_ts(
                        root, content_bytes, symbols, language=language, chart_location=filepath
                    )
                elif language == "go":
                    self._parse_go(
                        root, content_bytes, symbols, language=language, chart_location=filepath
                    )
                elif language == "rust":
                    self._parse_rust(
                        root, content_bytes, symbols, language=language, chart_location=filepath
                    )
                elif language == "java":
                    self._parse_java(
                        root, content_bytes, symbols, language=language, chart_location=filepath
                    )
                elif language in {"c", "cpp"}:
                    self._parse_c_cpp(
                        root, content_bytes, symbols, language=language, chart_location=filepath
                    )
                else:
                    self._parse_universal_tree_sitter(
                        root, content_bytes, symbols, language=language, chart_location=filepath
                    )
            except Exception:
                pass
        elif custom_visitor:
            try:
                custom_visitor(
                    self,
                    None,
                    content_bytes,
                    symbols,
                    parent_class=None,
                    language=language,
                    chart_location=filepath,
                )
            except Exception:
                pass

        # Tier 3: Universal Fallback if no parser available or if parsing yielded 0 symbols
        if not symbols and content_bytes.strip():
            symbols = self._parse_universal_fallback(content_bytes, filepath, ext)

        if not symbols and not parser and ext:
            self._skipped_extensions[ext] = self._skipped_extensions.get(ext, 0) + 1

        if mtime is not None:
            self._cache[filepath] = (mtime, symbols)
        self._remember_content(cache_key, symbols)

        return symbols

    def _get_node_text(self, node: Node, content_bytes: bytes) -> str:
        """Decode node text using Tree-sitter byte offsets (not Python str indices)."""
        try:
            return content_bytes[node.start_byte : node.end_byte].decode("utf-8")
        except Exception:
            return ""

    @staticmethod
    def _location_kwargs(node: Node) -> LocationKwargs:
        """Return one-based, end-exclusive source coordinates for a Tree-sitter node."""
        return {
            "start_line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
            "start_column": node.start_point[1] + 1,
            "end_column": node.end_point[1] + 1,
        }

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
        _ = content_bytes
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
            loc = self._location_kwargs(child)
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
                                    docstring = self._get_node_text(expr, content_bytes).strip(
                                        "\"'"
                                    )

                    body_blocks = self._extract_body_blocks(body_node, content_bytes)
                    structural_tokens = (
                        [b.node_type for b in body_blocks]
                        if body_blocks
                        else extract_tokens_from_body_text(body_text)
                    )
                    sym = CodeSymbol(
                        name=name_text,
                        type=SymbolType.FUNCTION,
                        **loc,
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
                    self._append_symbol(
                        symbols, sym, chart_location
                    )  # dsa:ignore per-symbol registration

            elif ctype == "class_definition":
                if name_node:
                    # Extract superclasses for signature
                    super_node = child.child_by_field_name("superclasses")
                    sig = self._get_node_text(super_node, content_bytes) if super_node else ""

                    sym = CodeSymbol(
                        name=name_text,
                        type=SymbolType.CLASS,
                        **loc,
                        signature=sig,
                        body=body_text,
                        parent_class=parent_class,
                        structural_tokens=self._extract_structural_tokens(body_node),
                        language=language,
                        chart_location=chart_location,
                    )
                    self._append_symbol(
                        symbols, sym, chart_location
                    )  # dsa:ignore per-symbol registration

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
                if parent_class is None:  # Only at module level for now
                    left_node = child.child_by_field_name("left")
                    if left_node and left_node.type == "identifier":
                        name = self._get_node_text(left_node, content_bytes)
                        # Heuristic: ALL_CAPS = Constant
                        stype = SymbolType.CONSTANT if name.isupper() else SymbolType.VARIABLE

                        symbols.append(
                            CodeSymbol(
                                name=name, type=stype, **loc, signature=name, body=child_text
                            )
                        )

            if ctype == "import_statement":
                # Use cached child_text
                text = child_text
                # Simple parsing: 'import os, sys'
                parts = text.replace("import", "").strip().split(",")
                for p in parts:
                    iname = p.strip().split(" as ")[0].strip()
                    symbols.append(
                        CodeSymbol(name=iname, type=SymbolType.IMPORT, **loc, module=iname)
                    )

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
                        for sub in child.children[import_keyword_idx + 1 :]:
                            sub_type = sub.type
                            if sub_type == "dotted_name":
                                imported_names.append(self._get_node_text(sub, content_bytes))
                            elif sub_type == "aliased_import":
                                sub_names = [
                                    self._get_node_text(n, content_bytes)
                                    for n in sub.children
                                    if n.type in {"identifier", "dotted_name"}
                                ]
                                if sub_names:
                                    imported_names.append(sub_names[0])
                            elif sub_type == "wildcard_import":
                                imported_names.append("*")

                    symbols.append(
                        CodeSymbol(
                            name=module_name,
                            type=SymbolType.IMPORT,
                            **loc,
                            module=module_name,
                            imported_names=imported_names,
                        )
                    )

            else:
                # Recurse for general containers (e.g. if statements, try/except block, etc. - unless already handled)
                if (
                    ctype
                    not in {
                        "function_definition",
                        "class_definition",
                        "import_statement",
                        "import_from_statement",
                    }
                    and child.children
                ):
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
            loc = self._location_kwargs(child)
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
                        **loc,
                        signature=sig,
                        body=body_text,
                        parent_class=parent_class,
                        calls=calls,
                        structural_tokens=structural_tokens,
                        body_blocks=body_blocks,
                        language=language,
                        chart_location=chart_location,
                    )
                    self._append_symbol(
                        symbols, sym, chart_location
                    )  # dsa:ignore per-symbol registration

            elif ctype == "class_declaration":
                if name_node:
                    # Inheritance
                    heritage_node = child.child_by_field_name("heritage")
                    sig = self._get_node_text(heritage_node, content_bytes) if heritage_node else ""

                    sym = CodeSymbol(
                        name=name_text,
                        type=SymbolType.CLASS,
                        **loc,
                        signature=sig,
                        body=body_text,
                        parent_class=parent_class,
                        structural_tokens=self._extract_structural_tokens(body_node),
                        language=language,
                        chart_location=chart_location,
                    )
                    self._append_symbol(
                        symbols, sym, chart_location
                    )  # dsa:ignore per-symbol registration

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
                module_name = (
                    self._get_node_text(source_node, content_bytes).strip("'\"")
                    if source_node
                    else ""
                )

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
                                    imported_names.append(
                                        self._get_node_text(sname_node, content_bytes)
                                    )
                                else:
                                    id_nodes = [n for n in spec.children if n.type == "identifier"]
                                    if id_nodes:
                                        imported_names.append(
                                            self._get_node_text(id_nodes[0], content_bytes)
                                        )

                    # check for namespace import (e.g. * as utils)
                    namespace = next(
                        (c for c in clause.children if c.type == "namespace_import"), None
                    )
                    if namespace:
                        id_nodes = [n for n in namespace.children if n.type == "identifier"]
                        if id_nodes:
                            imported_names.append(self._get_node_text(id_nodes[0], content_bytes))

                    # check for default identifier import
                    default_id = next((c for c in clause.children if c.type == "identifier"), None)
                    if default_id:
                        imported_names.append(self._get_node_text(default_id, content_bytes))

                symbols.append(
                    CodeSymbol(
                        name=module_name,
                        type=SymbolType.IMPORT,
                        **loc,
                        module=module_name,
                        imported_names=imported_names,
                    )
                )

            else:
                if (
                    ctype
                    not in {
                        "function_declaration",
                        "method_definition",
                        "class_declaration",
                        "import_statement",
                    }
                    and child.children
                ):
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
            loc = self._location_kwargs(child)
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
                        **loc,
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
                        **self._location_kwargs(spec),
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

    def _parse_rust(
        self,
        root: Node,
        content_bytes: bytes,
        symbols: list[CodeSymbol],
        parent_class: str | None = None,
        language: str = "rust",
        chart_location: str | None = None,
    ) -> None:
        """Recursively parses a Rust AST root node."""
        for child in root.children:
            loc = self._location_kwargs(child)
            ctype = child.type
            name_node = child.child_by_field_name("name")
            body_node = child.child_by_field_name("body")
            name_text = self._get_node_text(name_node, content_bytes) if name_node else ""
            body_text = self._get_node_text(body_node, content_bytes) if body_node else ""
            body_blocks = self._extract_body_blocks(body_node, content_bytes) if body_node else []

            if ctype in {"struct_item", "enum_item", "trait_item"}:
                if name_node:
                    sym = CodeSymbol(
                        name=name_text,
                        type=SymbolType.CLASS,
                        **loc,
                        signature=name_text,
                        body=body_text,
                        parent_class=parent_class,
                        structural_tokens=self._extract_structural_tokens(body_node),
                        body_blocks=body_blocks,
                        language=language,
                        chart_location=chart_location,
                    )
                    self._append_symbol(symbols, sym, chart_location)  # dsa:ignore

                    if ctype == "trait_item" and body_node:
                        self._parse_rust(
                            body_node,
                            content_bytes,
                            symbols,
                            parent_class=name_text,
                            language=language,
                            chart_location=chart_location,
                        )

            elif ctype == "impl_item":
                type_node = child.child_by_field_name("type")
                target_name: str | None = None
                if type_node:
                    target_name = self._get_node_text(type_node, content_bytes)
                if body_node:
                    self._parse_rust(
                        body_node,
                        content_bytes,
                        symbols,
                        parent_class=target_name or parent_class,
                        language=language,
                        chart_location=chart_location,
                    )

            elif ctype == "function_item":
                if name_node:
                    params_node = child.child_by_field_name("parameters")
                    sig = self._get_node_text(params_node, content_bytes) if params_node else "()"
                    ret_node = child.child_by_field_name("return_type")
                    if ret_node:
                        sig = f"{sig} -> {self._get_node_text(ret_node, content_bytes)}"

                    calls: list[str] = []
                    if body_node:
                        self._extract_calls(body_node, content_bytes, calls)

                    structural_tokens = (
                        [b.node_type for b in body_blocks]
                        if body_blocks
                        else extract_tokens_from_body_text(body_text)
                    )
                    sym = CodeSymbol(
                        name=name_text,
                        type=SymbolType.FUNCTION,
                        **loc,
                        signature=sig,
                        body=body_text,
                        parent_class=parent_class,
                        calls=calls,
                        structural_tokens=structural_tokens,
                        body_blocks=body_blocks,
                        language=language,
                        chart_location=chart_location,
                    )
                    self._append_symbol(symbols, sym, chart_location)  # dsa:ignore

            elif ctype == "use_declaration":
                arg = child.child_by_field_name("argument")
                use_text = self._get_node_text(arg, content_bytes) if arg else ""
                if not use_text:
                    use_text = (
                        self._get_node_text(child, content_bytes)
                        .replace("use", "")
                        .replace(";", "")
                        .strip()
                    )
                module_name = use_text.split("::")[0] if "::" in use_text else use_text
                sym = CodeSymbol(
                    name=use_text,
                    type=SymbolType.IMPORT,
                    **loc,
                    module=module_name,
                    imported_names=[use_text.split("::")[-1]] if "::" in use_text else [use_text],
                    language=language,
                    chart_location=chart_location,
                )
                self._append_symbol(symbols, sym, chart_location)  # dsa:ignore

            else:
                if (
                    ctype
                    not in {
                        "struct_item",
                        "enum_item",
                        "trait_item",
                        "impl_item",
                        "function_item",
                        "use_declaration",
                    }
                    and child.children
                ):
                    self._parse_rust(
                        child,
                        content_bytes,
                        symbols,
                        parent_class,
                        language=language,
                        chart_location=chart_location,
                    )

    def _parse_java(
        self,
        root: Node,
        content_bytes: bytes,
        symbols: list[CodeSymbol],
        parent_class: str | None = None,
        language: str = "java",
        chart_location: str | None = None,
    ) -> None:
        """Recursively parses a Java AST root node."""
        for child in root.children:
            loc = self._location_kwargs(child)
            ctype = child.type
            name_node = child.child_by_field_name("name")
            body_node = child.child_by_field_name("body")
            name_text = self._get_node_text(name_node, content_bytes) if name_node else ""
            body_text = self._get_node_text(body_node, content_bytes) if body_node else ""
            body_blocks = self._extract_body_blocks(body_node, content_bytes) if body_node else []

            if ctype in {
                "class_declaration",
                "interface_declaration",
                "enum_declaration",
                "record_declaration",
            }:
                if name_node:
                    super_node = child.child_by_field_name("superclass")
                    super_text = (
                        self._get_node_text(super_node, content_bytes) if super_node else ""
                    )

                    sym = CodeSymbol(
                        name=name_text,
                        type=SymbolType.CLASS,
                        **loc,
                        signature=super_text or name_text,
                        body=body_text,
                        parent_class=parent_class,
                        structural_tokens=self._extract_structural_tokens(body_node),
                        body_blocks=body_blocks,
                        language=language,
                        chart_location=chart_location,
                    )
                    self._append_symbol(symbols, sym, chart_location)  # dsa:ignore

                    if body_node:
                        self._parse_java(
                            body_node,
                            content_bytes,
                            symbols,
                            parent_class=name_text,
                            language=language,
                            chart_location=chart_location,
                        )

            elif ctype in {"method_declaration", "constructor_declaration"}:
                if name_node:
                    params_node = child.child_by_field_name("parameters")
                    sig = self._get_node_text(params_node, content_bytes) if params_node else "()"
                    ret_node = child.child_by_field_name("type")
                    if ret_node:
                        sig = f"{self._get_node_text(ret_node, content_bytes)} {name_text}{sig}"

                    calls: list[str] = []
                    if body_node:
                        self._extract_calls(body_node, content_bytes, calls)

                    structural_tokens = (
                        [b.node_type for b in body_blocks]
                        if body_blocks
                        else extract_tokens_from_body_text(body_text)
                    )
                    sym = CodeSymbol(
                        name=name_text,
                        type=SymbolType.FUNCTION,
                        **loc,
                        signature=sig,
                        body=body_text,
                        parent_class=parent_class,
                        calls=calls,
                        structural_tokens=structural_tokens,
                        body_blocks=body_blocks,
                        language=language,
                        chart_location=chart_location,
                    )
                    self._append_symbol(symbols, sym, chart_location)  # dsa:ignore

            elif ctype == "import_declaration":
                imp_text = (
                    self._get_node_text(child, content_bytes)
                    .replace("import", "")
                    .replace("static", "")
                    .replace(";", "")
                    .strip()
                )
                module_name = imp_text
                imported_names = [imp_text.split(".")[-1]] if "." in imp_text else [imp_text]
                sym = CodeSymbol(
                    name=imp_text,
                    type=SymbolType.IMPORT,
                    **loc,
                    module=module_name,
                    imported_names=imported_names,
                    language=language,
                    chart_location=chart_location,
                )
                self._append_symbol(symbols, sym, chart_location)  # dsa:ignore

            else:
                if (
                    ctype
                    not in {
                        "class_declaration",
                        "interface_declaration",
                        "enum_declaration",
                        "record_declaration",
                        "method_declaration",
                        "constructor_declaration",
                        "import_declaration",
                    }
                    and child.children
                ):
                    self._parse_java(
                        child,
                        content_bytes,
                        symbols,
                        parent_class,
                        language=language,
                        chart_location=chart_location,
                    )

    def _extract_c_cpp_declarator(self, decl_node: Node, content_bytes: bytes) -> tuple[str, str]:
        name = ""
        params = ""
        curr: Node | None = decl_node
        while curr:
            d_node = curr.child_by_field_name("declarator")
            c_type = curr.type
            if c_type == "function_declarator":
                p_node = curr.child_by_field_name("parameters")
                if p_node:
                    params = self._get_node_text(p_node, content_bytes)
                curr = d_node
            elif c_type in {"pointer_declarator", "reference_declarator"}:
                curr = d_node
            elif c_type in {"identifier", "field_identifier", "qualified_identifier"}:
                name = self._get_node_text(curr, content_bytes)
                break
            else:
                if d_node:
                    curr = d_node
                else:
                    name = self._get_node_text(curr, content_bytes)  # dsa:ignore
                    break
        return name, params

    def _parse_c_cpp(
        self,
        root: Node,
        content_bytes: bytes,
        symbols: list[CodeSymbol],
        parent_class: str | None = None,
        language: str = "cpp",
        chart_location: str | None = None,
    ) -> None:
        """Recursively parses a C / C++ AST root node."""
        for child in root.children:
            loc = self._location_kwargs(child)
            ctype = child.type
            name_node = child.child_by_field_name("name")
            body_node = child.child_by_field_name("body")
            name_text = self._get_node_text(name_node, content_bytes) if name_node else ""
            body_text = self._get_node_text(body_node, content_bytes) if body_node else ""
            body_blocks = self._extract_body_blocks(body_node, content_bytes) if body_node else []

            if ctype in {"class_specifier", "struct_specifier"}:
                if name_node:
                    sym = CodeSymbol(
                        name=name_text,
                        type=SymbolType.CLASS,
                        **loc,
                        signature=name_text,
                        body=body_text,
                        parent_class=parent_class,
                        structural_tokens=self._extract_structural_tokens(body_node),
                        body_blocks=body_blocks,
                        language=language,
                        chart_location=chart_location,
                    )
                    self._append_symbol(symbols, sym, chart_location)  # dsa:ignore

                    if body_node:
                        self._parse_c_cpp(
                            body_node,
                            content_bytes,
                            symbols,
                            parent_class=name_text,
                            language=language,
                            chart_location=chart_location,
                        )

            elif ctype == "function_definition":
                decl_node = child.child_by_field_name("declarator")
                if decl_node:
                    func_name, params_str = self._extract_c_cpp_declarator(decl_node, content_bytes)
                    if func_name:
                        calls: list[str] = []
                        if body_node:
                            self._extract_calls(body_node, content_bytes, calls)

                        structural_tokens = (
                            [b.node_type for b in body_blocks]
                            if body_blocks
                            else extract_tokens_from_body_text(body_text)
                        )

                        parent = parent_class
                        actual_name = func_name
                        if "::" in func_name:
                            parts = func_name.split("::")
                            parent = parts[0]
                            actual_name = parts[-1]

                        sym = CodeSymbol(
                            name=actual_name,
                            type=SymbolType.FUNCTION,
                            **loc,
                            signature=params_str or "()",
                            body=body_text,
                            parent_class=parent,
                            calls=calls,
                            structural_tokens=structural_tokens,
                            body_blocks=body_blocks,
                            language=language,
                            chart_location=chart_location,
                        )
                        self._append_symbol(symbols, sym, chart_location)  # dsa:ignore

            elif ctype == "preproc_include":
                path_node = child.child_by_field_name("path")
                path_text = self._get_node_text(path_node, content_bytes) if path_node else ""
                if not path_text:
                    path_text = (
                        self._get_node_text(child, content_bytes).replace("#include", "").strip()
                    )
                cleaned = path_text.strip('<">')
                sym = CodeSymbol(
                    name=cleaned,
                    type=SymbolType.IMPORT,
                    **loc,
                    module=cleaned,
                    imported_names=[cleaned],
                    language=language,
                    chart_location=chart_location,
                )
                self._append_symbol(symbols, sym, chart_location)  # dsa:ignore

            else:
                if (
                    ctype
                    not in {
                        "class_specifier",
                        "struct_specifier",
                        "function_definition",
                        "preproc_include",
                    }
                    and child.children
                ):
                    self._parse_c_cpp(
                        child,
                        content_bytes,
                        symbols,
                        parent_class,
                        language=language,
                        chart_location=chart_location,
                    )

    _TS_FUNCTION_TYPES = frozenset(
        {
            "function_item",
            "function_declaration",
            "function_definition",
            "method_declaration",
            "method_definition",
            "subroutine",
            "func_literal",
        }
    )
    _TS_CLASS_TYPES = frozenset(
        {
            "class_declaration",
            "class_definition",
            "class_specifier",
            "struct_item",
            "struct_specifier",
            "interface_declaration",
            "type_declaration",
            "type_spec",
            "type_definition",
            "enum_item",
            "enum_declaration",
            "record_declaration",
            "trait_item",
        }
    )
    _TS_IMPORT_TYPES = frozenset(
        {
            "use_declaration",
            "import_declaration",
            "import_statement",
            "preproc_include",
            "include_statement",
        }
    )

    def _parse_universal_tree_sitter(
        self,
        root: Node,
        content_bytes: bytes,
        symbols: list[CodeSymbol],
        parent_class: str | None = None,
        language: str = "unknown",
        chart_location: str | None = None,
    ) -> None:
        """Universal Tree-sitter node walker for any registered grammar."""
        for child in root.children:
            loc = self._location_kwargs(child)
            ctype = child.type
            name_node = child.child_by_field_name("name")
            body_node = child.child_by_field_name("body") or child.child_by_field_name("type")
            body_text = self._get_node_text(body_node, content_bytes) if body_node else ""
            body_blocks = self._extract_body_blocks(body_node, content_bytes) if body_node else []

            if ctype in self._TS_CLASS_TYPES:
                if not name_node:
                    for sub in child.children:
                        if sub.type in {"type_identifier", "identifier"}:
                            name_node = sub
                            break
                if name_node:
                    name_text = self._get_node_text(name_node, content_bytes)
                    sym = CodeSymbol(
                        name=name_text,
                        type=SymbolType.CLASS,
                        **loc,
                        signature=name_text,
                        body=body_text,
                        parent_class=parent_class,
                        structural_tokens=self._extract_structural_tokens(body_node),
                        body_blocks=body_blocks,
                        language=language,
                        chart_location=chart_location,
                    )
                    self._append_symbol(symbols, sym, chart_location)  # dsa:ignore

                    if body_node:
                        self._parse_universal_tree_sitter(
                            body_node,
                            content_bytes,
                            symbols,
                            parent_class=name_text,
                            language=language,
                            chart_location=chart_location,
                        )
                elif child.children:
                    self._parse_universal_tree_sitter(
                        child,
                        content_bytes,
                        symbols,
                        parent_class=parent_class,
                        language=language,
                        chart_location=chart_location,
                    )  # dsa:ignore

            elif ctype in self._TS_FUNCTION_TYPES:
                if not name_node:
                    for sub in child.children:
                        if sub.type in {"identifier", "field_identifier"}:
                            name_node = sub
                            break
                if name_node:
                    name_text = self._get_node_text(name_node, content_bytes)  # dsa:ignore
                    params_node = child.child_by_field_name("parameters")
                    sig = self._get_node_text(params_node, content_bytes) if params_node else "()"
                    calls: list[str] = []
                    if body_node:
                        self._extract_calls(body_node, content_bytes, calls)

                    structural_tokens = (
                        [b.node_type for b in body_blocks]
                        if body_blocks
                        else extract_tokens_from_body_text(body_text)
                    )
                    sym = CodeSymbol(
                        name=name_text,
                        type=SymbolType.FUNCTION,
                        **loc,
                        signature=sig,
                        body=body_text,
                        parent_class=parent_class,
                        calls=calls,
                        structural_tokens=structural_tokens,
                        body_blocks=body_blocks,
                        language=language,
                        chart_location=chart_location,
                    )
                    self._append_symbol(symbols, sym, chart_location)  # dsa:ignore

            elif ctype in self._TS_IMPORT_TYPES:
                child_text = self._get_node_text(child, content_bytes).strip()
                sym = CodeSymbol(
                    name=child_text,
                    type=SymbolType.IMPORT,
                    **loc,
                    module=child_text,
                    imported_names=[child_text],
                    language=language,
                    chart_location=chart_location,
                )
                self._append_symbol(symbols, sym, chart_location)  # dsa:ignore

            else:
                if (
                    child.children
                    and ctype not in self._TS_CLASS_TYPES
                    and ctype not in self._TS_FUNCTION_TYPES
                ):
                    self._parse_universal_tree_sitter(  # dsa:ignore
                        child,
                        content_bytes,
                        symbols,
                        parent_class=parent_class,
                        language=language,
                        chart_location=chart_location,
                    )  # dsa:ignore

    _RUBY_LIKE_EXTS = frozenset({".rb", ".ruby", ".rake", ".gemspec", ".lua", ".ex", ".exs"})
    _SHELL_EXTS = frozenset({".sh", ".bash", ".zsh"})

    _CLASS_DECL_RE = re.compile(
        r"^\s*(?:(?:export|public|private|protected|final|abstract|sealed)\s+)*(class|struct|interface|trait|module|record)\s+([A-Za-z0-9_:]+)"
    )
    _FUNC_KW_RE = re.compile(
        r"^\s*(?:(?:export|public|private|protected|static|async|override|virtual)\s+)*(?:def|fn|func|function|sub)\s+([A-Za-z0-9_!?=]+)\s*(\([^)]*\))?"
    )
    _SHELL_FUNC_PAREN_RE = re.compile(r"^\s*(?:function\s+)?([A-Za-z0-9_-]+)\s*\(\)\s*\{?")
    _SHELL_FUNC_KW_RE = re.compile(r"^\s*function\s+([A-Za-z0-9_-]+)\s*(?:\(\))?\s*\{?")
    _C_STYLE_FUNC_RE = re.compile(
        r"^\s*(?:(?:export|public|private|protected|static|inline|virtual)\s+)*(?:[A-Za-z0-9_<>[\]*&]+\s+)+([A-Za-z0-9_]+)\s*(\([^)]*\))\s*\{?"
    )
    _IMPORT_DECL_RE = re.compile(
        r"^\s*(?:(?:require|require_relative|use|import|source|\.)\s+['\"]?([A-Za-z0-9_.:/\\-]+)['\"]?)"
    )
    _RUBY_DEPTH_TOKENS_RE = re.compile(
        r"\b(?:class|module|def|if|unless|while|until|case|for|begin|do|end)\b"
    )
    _RUBY_INC_KEYWORDS = frozenset(
        {"class", "module", "def", "if", "unless", "while", "until", "case", "for", "begin", "do"}
    )

    def _parse_universal_fallback(
        self,
        content_bytes: bytes,
        filepath: str,
        ext: str,
    ) -> list[CodeSymbol]:
        """Universal structural block fallback scanning for languages without Tree-sitter."""
        try:
            content_str = content_bytes.decode("utf-8", errors="replace")
        except Exception:
            return []

        lines = content_str.splitlines()
        total_lines = len(lines)
        if total_lines == 0:
            return []

        is_ruby_like = ext in self._RUBY_LIKE_EXTS
        is_shell = ext in self._SHELL_EXTS
        language = self._language_for_ext(ext)
        if language == "unknown" and ext:
            language = ext.lstrip(".")

        symbols: list[CodeSymbol] = []
        scope_stack: list[dict[str, Any]] = []
        open_items: list[dict[str, Any]] = []

        current_brace_depth = 0
        current_ruby_depth = 0

        for idx, line in enumerate(lines):
            line_num = idx + 1
            line_len = len(line)
            end_col = line_len + 1
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("//"):
                continue

            parent_class: str | None = None
            for s in reversed(scope_stack):
                if s["type"] == SymbolType.CLASS:
                    parent_class = s["name"]
                    break

            # 1. Imports
            im_match = self._IMPORT_DECL_RE.match(line)
            if im_match:
                imp_name = im_match.group(1)
                sym = CodeSymbol(
                    name=imp_name,
                    type=SymbolType.IMPORT,
                    start_line=line_num,
                    end_line=line_num,
                    start_column=1,
                    end_column=end_col,
                    module=imp_name,
                    imported_names=[imp_name],
                    language=language,
                    chart_location=filepath,
                )
                self._append_symbol(symbols, sym, filepath)  # dsa:ignore

            # 2. Classes
            cm = self._CLASS_DECL_RE.match(line)
            if cm:
                cname = cm.group(2)
                item = {
                    "type": SymbolType.CLASS,
                    "name": cname,
                    "start_line": line_num,
                    "start_column": line.find(cname) + 1 if cname in line else 1,
                    "end_column": end_col,
                    "parent_class": parent_class,
                    "signature": stripped,
                    "lines": [line],
                    "brace_depth": current_brace_depth,
                    "ruby_depth": current_ruby_depth,
                }
                open_items.append(item)
                scope_stack.append(item)
            else:
                # 3. Functions
                fname: str | None = None
                sig: str | None = None

                fm_kw = self._FUNC_KW_RE.match(line)
                if fm_kw:
                    fname = fm_kw.group(1)
                    sig = fm_kw.group(2) or "()"
                elif is_shell:
                    fm_sh1 = self._SHELL_FUNC_PAREN_RE.match(line)
                    fm_sh2 = self._SHELL_FUNC_KW_RE.match(line)
                    if fm_sh1:
                        fname = fm_sh1.group(1)
                        sig = "()"
                    elif fm_sh2:
                        fname = fm_sh2.group(1)
                        sig = "()"
                else:
                    fm_c = self._C_STYLE_FUNC_RE.match(line)
                    if fm_c:
                        candidate = fm_c.group(1)
                        if candidate not in {"if", "while", "for", "switch", "catch"}:
                            fname = candidate
                            sig = fm_c.group(2) or "()"

                if fname:
                    item = {
                        "type": SymbolType.FUNCTION,
                        "name": fname,
                        "start_line": line_num,
                        "start_column": line.find(fname) + 1 if fname in line else 1,
                        "end_column": end_col,
                        "parent_class": parent_class,
                        "signature": sig,
                        "lines": [line],
                        "brace_depth": current_brace_depth,
                        "ruby_depth": current_ruby_depth,
                    }
                    open_items.append(item)
                    scope_stack.append(item)

            for sc in scope_stack:
                if sc["start_line"] != line_num:
                    sc["lines"].append(line)

            if is_ruby_like:
                tokens = self._RUBY_DEPTH_TOKENS_RE.findall(line)
                for t in tokens:
                    if t in self._RUBY_INC_KEYWORDS:
                        current_ruby_depth += 1
                    elif t == "end":
                        current_ruby_depth -= 1
                        while scope_stack and scope_stack[-1]["ruby_depth"] >= current_ruby_depth:
                            closed = scope_stack.pop()
                            closed["end_line"] = line_num
            else:
                opens = line.count("{")
                closes = line.count("}")
                current_brace_depth += opens - closes
                while (
                    scope_stack
                    and current_brace_depth <= scope_stack[-1]["brace_depth"]
                    and closes > 0
                ):
                    closed = scope_stack.pop()
                    closed["end_line"] = line_num

        for item in open_items:
            end_line = item.get("end_line", total_lines)
            body_text = "\n".join(item.get("lines", []))
            sym = CodeSymbol(
                name=item["name"],
                type=item["type"],
                start_line=item["start_line"],
                end_line=end_line,
                start_column=item.get("start_column", 1),
                end_column=item.get("end_column", 1),
                signature=item.get("signature", item["name"]),
                body=body_text,
                parent_class=item.get("parent_class"),
                structural_tokens=extract_tokens_from_body_text(body_text),
                language=language,
                chart_location=filepath,
            )
            self._append_symbol(symbols, sym, filepath)  # dsa:ignore

        return symbols
