import re

from gdss.core.structural_fingerprint import (
    extract_tokens_from_body_text,
    fingerprint_bucket,
    normalized_similarity,
)
from gdss.core.symbol_identity import (
    compute_symbol_id,  # noqa: F401 - reserved for future ID helpers
)
from gdss.core.transform_types import CodeSymbol, OperatorType, SemanticOperator, SymbolType

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_STUB_TOKEN_TYPES = frozenset({"pass_statement", "expression_statement"})


class TransformExtractor:
    """
    Engine to extract semantic transformation operators by comparing AST states (CodeSymbol sets)
    between two versions of a source file.
    """

    def __init__(self, rename_threshold: float = 0.65):
        self.rename_threshold = rename_threshold

    @staticmethod
    def _symbol_key(sym: CodeSymbol) -> tuple[str, str]:
        """Stable map key: (parent_class, name) avoids collisions across classes."""
        return (sym.parent_class or "", sym.name)

    @staticmethod
    def _symbol_map(symbols: list[CodeSymbol]) -> dict[tuple[str, str], CodeSymbol]:
        return {TransformExtractor._symbol_key(s): s for s in symbols}

    @staticmethod
    def _is_valid_identifier(name: str | None) -> bool:
        return name is not None and bool(_IDENTIFIER_RE.match(name))

    def _is_near_empty_stub(self, sym: CodeSymbol) -> bool:
        tokens = self._structural_profile(sym)
        if not tokens:
            return True
        if len(tokens) == 1 and tokens[0] in _STUB_TOKEN_TYPES:
            return True
        # pass-only bodies are structurally empty regardless of formatting
        stripped = (sym.body or "").strip()
        if stripped.endswith("pass") and "\n" in stripped:
            body_lines = [ln.strip() for ln in stripped.splitlines()[1:] if ln.strip()]
            if body_lines and all(ln == "pass" for ln in body_lines):
                return True
        return False

    def _rename_allowed(self, del_sym: CodeSymbol, add_sym: CodeSymbol, score: float) -> bool:
        if not self._is_valid_identifier(del_sym.name) or not self._is_valid_identifier(
            add_sym.name
        ):
            return False
        if del_sym.name == add_sym.name:
            return False
        # Near-empty stubs look identical under structural fingerprints — reject.
        if self._is_near_empty_stub(del_sym) and self._is_near_empty_stub(add_sym):
            return False
        # Require clear structural agreement for a rename claim.
        if score < self.rename_threshold:
            return False
        return True

    def extract_operators(
        self,
        file_path: str,
        old_symbols: list[CodeSymbol],
        new_symbols: list[CodeSymbol],
        commit_sha: str = "",
    ) -> list[SemanticOperator]:
        for sym in old_symbols + new_symbols:
            sym.ensure_identity(file_path)

        operators: list[SemanticOperator] = []

        old_funcs = [s for s in old_symbols if s.type == SymbolType.FUNCTION]
        new_funcs = [s for s in new_symbols if s.type == SymbolType.FUNCTION]
        old_classes = [s for s in old_symbols if s.type == SymbolType.CLASS]
        new_classes = [s for s in new_symbols if s.type == SymbolType.CLASS]
        old_imports = [s for s in old_symbols if s.type == SymbolType.IMPORT]
        new_imports = [s for s in new_symbols if s.type == SymbolType.IMPORT]
        old_vars = [s for s in old_symbols if s.type in {SymbolType.VARIABLE, SymbolType.CONSTANT}]
        new_vars = [s for s in new_symbols if s.type in {SymbolType.VARIABLE, SymbolType.CONSTANT}]

        self._extract_function_ops(file_path, old_funcs, new_funcs, operators, commit_sha)
        self._extract_class_ops(file_path, old_classes, new_classes, operators, commit_sha)
        self._extract_import_ops(file_path, old_imports, new_imports, operators, commit_sha)
        self._extract_variable_ops(file_path, old_vars, new_vars, operators, commit_sha)

        return operators

    def _structural_profile(self, sym: CodeSymbol) -> list[str]:
        if sym.body_blocks:
            profile: list[str] = []
            for block in sym.body_blocks:
                profile.extend(block.structural_tokens or [block.node_type])
            if profile:
                return profile
        if sym.structural_tokens:
            return sym.structural_tokens
        return extract_tokens_from_body_text(sym.body)

    def _compute_structural_similarity(self, a: CodeSymbol, b: CodeSymbol) -> float:
        tokens_a = self._structural_profile(a)
        tokens_b = self._structural_profile(b)
        token_sim = normalized_similarity(tokens_a, tokens_b)
        if token_sim < self.rename_threshold:
            return token_sim

        sig_match = 1.0 if a.signature == b.signature else 0.0
        a_span = max(a.end_line - a.start_line, 1)
        b_span = max(b.end_line - b.start_line, 1)
        max_span = max(a_span, b_span)
        line_sim = 1.0 - abs(a_span - b_span) / max_span
        len_a = len(tokens_a)
        len_b = len(tokens_b)
        count_sim = min(len_a, len_b) / max(len_a, len_b, 1)

        return (0.55 * token_sim) + (0.2 * sig_match) + (0.15 * line_sim) + (0.1 * count_sim)

    def _changed_blocks(self, old_sym: CodeSymbol, new_sym: CodeSymbol) -> list[str]:
        old_map = {b.block_id: b for b in old_sym.body_blocks}
        new_map = {b.block_id: b for b in new_sym.body_blocks}
        changed: list[str] = []

        for block_id, old_block in old_map.items():
            new_block = new_map.get(block_id)
            if new_block is None:
                changed.append(block_id)
                continue
            if old_block.structural_tokens != new_block.structural_tokens:
                changed.append(block_id)
            elif (
                old_block.start_line != new_block.start_line
                or old_block.end_line != new_block.end_line
            ):
                # formatting-only line shift within same block shape
                pass

        for block_id in new_map:
            if block_id not in old_map:
                changed.append(block_id)
        return sorted(changed)

    def _build_rename_buckets(self, symbols: list[CodeSymbol]) -> dict[str, list[CodeSymbol]]:
        buckets: dict[str, list[CodeSymbol]] = {}
        for sym in symbols:
            bucket = fingerprint_bucket(self._structural_profile(sym))
            buckets.setdefault(bucket, []).append(sym)
        return buckets

    def _extract_variable_ops(
        self,
        file: str,
        old_list: list[CodeSymbol],
        new_list: list[CodeSymbol],
        operators: list[SemanticOperator],
        commit: str,
    ):
        old_map = self._symbol_map(old_list)
        new_map = self._symbol_map(new_list)
        old_keys = set(old_map.keys())
        new_keys = set(new_map.keys())
        deleted = old_keys - new_keys
        added = new_keys - old_keys
        common = old_keys & new_keys

        for key in sorted(common):
            old_sym = old_map[key]
            new_sym = new_map[key]
            if old_sym.body != new_sym.body:
                op_type = (
                    OperatorType.MODIFY_CONSTANT
                    if old_sym.type == SymbolType.CONSTANT
                    else OperatorType.MODIFY_VARIABLE
                )
                operators.append(
                    SemanticOperator(
                        operator=op_type,
                        file=file,
                        commit=commit,
                        name=old_sym.name,
                        details={"old_value": old_sym.body, "new_value": new_sym.body},
                    )
                )

        for key in sorted(deleted):
            operators.append(
                SemanticOperator(
                    OperatorType.REMOVE_DEPENDENCY, file, commit, name=old_map[key].name
                )
            )
        for key in sorted(added):
            operators.append(
                SemanticOperator(OperatorType.ADD_DEPENDENCY, file, commit, name=new_map[key].name)
            )

    def extract_repo_operators(
        self, old_files: list[str], new_files: list[str], commit_sha: str = ""
    ) -> list[SemanticOperator]:
        import os

        operators: list[SemanticOperator] = []
        old_set = set(old_files)
        new_set = set(new_files)
        deleted = old_set - new_set
        added = new_set - old_set
        deleted_list = sorted(deleted)
        added_list = sorted(added)

        for del_f in deleted_list:
            del_base = os.path.basename(del_f)
            for add_f in added_list:
                if add_f not in added:
                    continue
                add_base = os.path.basename(add_f)
                if del_base == add_base:
                    operators.append(
                        SemanticOperator(
                            operator=OperatorType.RENAME_FILE,
                            file=add_f,
                            from_name=del_f,
                            to_name=add_f,
                            commit=commit_sha,
                        )
                    )
                    added.remove(add_f)
                    deleted.remove(del_f)
                    break

        for f in deleted_list:
            if f in deleted:
                operators.append(SemanticOperator(OperatorType.DELETE_FILE, f, commit=commit_sha))
        for f in added_list:
            if f in added:
                operators.append(SemanticOperator(OperatorType.ADD_FILE, f, commit=commit_sha))
        return operators

    def _match_symbol_renames(
        self,
        old_map: dict[tuple[str, str], CodeSymbol],
        new_map: dict[tuple[str, str], CodeSymbol],
        deleted_keys: set[tuple[str, str]],
        added_keys: set[tuple[str, str]],
    ) -> list[tuple[tuple[str, str], tuple[str, str], float]]:
        deleted_syms = [old_map[k] for k in deleted_keys]
        added_by_bucket = self._build_rename_buckets([new_map[k] for k in added_keys])
        key_of = self._symbol_key

        candidates: list[tuple[float, tuple[str, str], tuple[str, str]]] = []
        for del_sym in deleted_syms:
            del_key = key_of(del_sym)
            bucket = fingerprint_bucket(self._structural_profile(del_sym))
            # Empty bucket (no tokens) — fall back to full added set is unsafe; skip.
            pool = added_by_bucket.get(bucket, []) if bucket else []
            for add_sym in pool:
                if del_sym.parent_class != add_sym.parent_class:
                    continue
                add_key = key_of(add_sym)
                if add_key not in added_keys:
                    continue
                score = self._compute_structural_similarity(del_sym, add_sym)
                if not self._rename_allowed(del_sym, add_sym, score):
                    continue
                candidates.append((score, del_key, add_key))

        candidates.sort(reverse=True, key=lambda item: item[0])
        used: set[str] = set()
        matches: list[tuple[tuple[str, str], tuple[str, str], float]] = []
        for score, del_key, add_key in candidates:
            del_mark = f"deleted:{del_key}"
            add_mark = f"added:{add_key}"
            if del_mark in used or add_mark in used:
                continue
            used.add(del_mark)
            used.add(add_mark)
            matches.append((del_key, add_key, score))
        return matches

    def _extract_function_ops(
        self,
        file: str,
        old_list: list[CodeSymbol],
        new_list: list[CodeSymbol],
        operators: list[SemanticOperator],
        commit: str,
    ):
        old_map = self._symbol_map(old_list)
        new_map = self._symbol_map(new_list)
        deleted_keys = set(old_map.keys()) - set(new_map.keys())
        added_keys = set(new_map.keys()) - set(old_map.keys())

        rename_pairs = self._match_symbol_renames(old_map, new_map, deleted_keys, added_keys)
        for del_key, add_key, score in rename_pairs:
            del_sym = old_map[del_key]
            add_sym = new_map[add_key]
            deleted_keys.remove(del_key)
            added_keys.remove(add_key)
            operators.append(
                SemanticOperator(
                    operator=OperatorType.RENAME_FUNCTION,
                    file=file,
                    commit=commit,
                    from_name=del_sym.name,
                    to_name=add_sym.name,
                    from_symbol_id=del_sym.symbol_id,
                    to_symbol_id=add_sym.symbol_id,
                    details={
                        "similarity": round(score, 3),
                        "parent_class": del_sym.parent_class,
                        "method": "levenshtein_tokens",
                    },
                )
            )

        for key in sorted(set(old_map.keys()) & set(new_map.keys())):
            old_sym = old_map[key]
            new_sym = new_map[key]
            sig_changed = old_sym.signature != new_sym.signature
            changed_blocks = self._changed_blocks(old_sym, new_sym)
            body_changed = bool(changed_blocks) or (
                not old_sym.body_blocks
                and not new_sym.body_blocks
                and self._structural_profile(old_sym) != self._structural_profile(new_sym)
            )

            if sig_changed or body_changed:
                operators.append(
                    SemanticOperator(
                        operator=OperatorType.MODIFY_FUNCTION,
                        file=file,
                        commit=commit,
                        name=old_sym.name,
                        symbol_id=new_sym.symbol_id,
                        details={
                            "signature_changed": sig_changed,
                            "body_changed": body_changed,
                            "changed_blocks": changed_blocks,
                            "parent_class": old_sym.parent_class,
                            "old_signature": old_sym.signature,
                            "new_signature": new_sym.signature,
                        },
                    )
                )

        for key in sorted(deleted_keys):
            sym = old_map[key]
            operators.append(
                SemanticOperator(
                    operator=OperatorType.DELETE_FUNCTION,
                    file=file,
                    commit=commit,
                    name=sym.name,
                    symbol_id=sym.symbol_id,
                    details={"parent_class": sym.parent_class},
                )
            )

        for key in sorted(added_keys):
            sym = new_map[key]
            operators.append(
                SemanticOperator(
                    operator=OperatorType.ADD_FUNCTION,
                    file=file,
                    commit=commit,
                    name=sym.name,
                    symbol_id=sym.symbol_id,
                    details={"parent_class": sym.parent_class, "signature": sym.signature},
                )
            )

    def _extract_class_ops(
        self,
        file: str,
        old_list: list[CodeSymbol],
        new_list: list[CodeSymbol],
        operators: list[SemanticOperator],
        commit: str,
    ):
        old_map = self._symbol_map(old_list)
        new_map = self._symbol_map(new_list)
        deleted_keys = set(old_map.keys()) - set(new_map.keys())
        added_keys = set(new_map.keys()) - set(old_map.keys())

        rename_pairs = self._match_symbol_renames(old_map, new_map, deleted_keys, added_keys)
        for del_key, add_key, score in rename_pairs:
            del_sym = old_map[del_key]
            add_sym = new_map[add_key]
            deleted_keys.remove(del_key)
            added_keys.remove(add_key)
            operators.append(
                SemanticOperator(
                    operator=OperatorType.RENAME_CLASS,
                    file=file,
                    commit=commit,
                    from_name=del_sym.name,
                    to_name=add_sym.name,
                    from_symbol_id=del_sym.symbol_id,
                    to_symbol_id=add_sym.symbol_id,
                    details={"similarity": round(score, 3), "method": "levenshtein_tokens"},
                )
            )

        for key in sorted(set(old_map.keys()) & set(new_map.keys())):
            old_sym = old_map[key]
            new_sym = new_map[key]
            sig_changed = old_sym.signature != new_sym.signature
            body_changed = self._structural_profile(old_sym) != self._structural_profile(new_sym)
            if sig_changed or body_changed:
                operators.append(
                    SemanticOperator(
                        operator=OperatorType.MODIFY_CLASS,
                        file=file,
                        commit=commit,
                        name=old_sym.name,
                        symbol_id=new_sym.symbol_id,
                        details={
                            "signature_changed": sig_changed,
                            "body_changed": body_changed,
                            "old_signature": old_sym.signature,
                            "new_signature": new_sym.signature,
                        },
                    )
                )

        for key in sorted(deleted_keys):
            sym = old_map[key]
            operators.append(
                SemanticOperator(
                    operator=OperatorType.DELETE_CLASS,
                    file=file,
                    commit=commit,
                    name=sym.name,
                    symbol_id=sym.symbol_id,
                )
            )

        for key in sorted(added_keys):
            sym = new_map[key]
            operators.append(
                SemanticOperator(
                    operator=OperatorType.ADD_CLASS,
                    file=file,
                    commit=commit,
                    name=sym.name,
                    symbol_id=sym.symbol_id,
                )
            )

    def _extract_import_ops(
        self,
        file: str,
        old_list: list[CodeSymbol],
        new_list: list[CodeSymbol],
        operators: list[SemanticOperator],
        commit: str,
    ):
        old_modules = {s.module: s for s in old_list if s.module}
        new_modules = {s.module: s for s in new_list if s.module}
        old_keys = set(old_modules.keys())
        new_keys = set(new_modules.keys())
        deleted_imports = old_keys - new_keys
        added_imports = new_keys - old_keys
        common_imports = old_keys & new_keys

        for mod in sorted(common_imports):
            old_sym = old_modules[mod]
            new_sym = new_modules[mod]
            old_names = set(old_sym.imported_names)
            new_names = set(new_sym.imported_names)
            added_names = new_names - old_names
            removed_names = old_names - new_names
            if added_names or removed_names:
                operators.append(
                    SemanticOperator(
                        operator=OperatorType.MODIFY_DEPENDENCY,
                        file=file,
                        commit=commit,
                        name=mod,
                        details={
                            "added_names": list(added_names),
                            "removed_names": list(removed_names),
                        },
                    )
                )

        for mod in sorted(deleted_imports):
            sym = old_modules[mod]
            operators.append(
                SemanticOperator(
                    operator=OperatorType.REMOVE_IMPORT,
                    file=file,
                    commit=commit,
                    name=mod,
                    details={"imported_names": sym.imported_names},
                )
            )

        for mod in sorted(added_imports):
            sym = new_modules[mod]
            operators.append(
                SemanticOperator(
                    operator=OperatorType.ADD_IMPORT,
                    file=file,
                    commit=commit,
                    name=mod,
                    details={"imported_names": sym.imported_names},
                )
            )
