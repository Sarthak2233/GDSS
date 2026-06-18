import difflib
from typing import List, Dict, Set, Tuple, Any
from gdss.core.transform_types import CodeSymbol, SymbolType, SemanticOperator, OperatorType

class TransformExtractor:
    """
    Engine to extract semantic transformation operators by comparing AST states (CodeSymbol sets)
    between two versions of a source file.
    """

    def __init__(self, rename_threshold: float = 0.65):
        self.rename_threshold = rename_threshold

    def extract_operators(self, file_path: str, old_symbols: List[CodeSymbol], new_symbols: List[CodeSymbol], commit_sha: str = "") -> List[SemanticOperator]:
        operators: List[SemanticOperator] = []
        
        # 1. Separate by type
        old_funcs = [s for s in old_symbols if s.type == SymbolType.FUNCTION]
        new_funcs = [s for s in new_symbols if s.type == SymbolType.FUNCTION]

        old_classes = [s for s in old_symbols if s.type == SymbolType.CLASS]
        new_classes = [s for s in new_symbols if s.type == SymbolType.CLASS]

        old_imports = [s for s in old_symbols if s.type == SymbolType.IMPORT]
        new_imports = [s for s in new_symbols if s.type == SymbolType.IMPORT]
        
        old_vars = [s for s in old_symbols if s.type in {SymbolType.VARIABLE, SymbolType.CONSTANT}]
        new_vars = [s for s in new_symbols if s.type in {SymbolType.VARIABLE, SymbolType.CONSTANT}]

        # 2. Extract Function Operators (including Rename Heuristics)
        self._extract_function_ops(file_path, old_funcs, new_funcs, operators, commit_sha)

        # 3. Extract Class Operators (including Rename Heuristics)
        self._extract_class_ops(file_path, old_classes, new_classes, operators, commit_sha)

        # 4. Extract Import/Dependency Operators
        self._extract_import_ops(file_path, old_imports, new_imports, operators, commit_sha)
        
        # 5. Extract Variable/Constant Operators
        self._extract_variable_ops(file_path, old_vars, new_vars, operators, commit_sha)

        return operators

    def _extract_variable_ops(self, file: str, old_list: List[CodeSymbol], new_list: List[CodeSymbol], operators: List[SemanticOperator], commit: str):
        old_map = {s.name: s for s in old_list}
        new_map = {s.name: s for s in new_list}
        
        old_keys = set(old_map.keys())
        new_keys = set(new_map.keys())
        
        deleted = old_keys - new_keys
        added = new_keys - old_keys
        common = old_keys & new_keys
        
        for name in sorted(list(common)):
            old_sym = old_map[name]
            new_sym = new_map[name]
            if old_sym.body != new_sym.body:
                op_type = OperatorType.MODIFY_CONSTANT if old_sym.type == SymbolType.CONSTANT else OperatorType.MODIFY_VARIABLE
                operators.append(SemanticOperator(
                    operator=op_type,
                    file=file,
                    commit=commit,
                    name=name,
                    details={"old_value": old_sym.body, "new_value": new_sym.body}
                ))
        
        for name in sorted(list(deleted)):
            operators.append(SemanticOperator(OperatorType.REMOVE_DEPENDENCY, file, commit, name=name))
        for name in sorted(list(added)):
            operators.append(SemanticOperator(OperatorType.ADD_DEPENDENCY, file, commit, name=name))

    def extract_repo_operators(self, old_files: List[str], new_files: List[str], commit_sha: str = "") -> List[SemanticOperator]:
        """
        Detects file-level semantic operators (ADD_FILE, DELETE_FILE, RENAME_FILE).
        """
        import os
        operators: List[SemanticOperator] = []
        old_set = set(old_files)
        new_set = set(new_files)

        deleted = old_set - new_set
        added = new_set - old_set
        
        # DSA: convert to lists once
        deleted_list = sorted(list(deleted))
        added_list = sorted(list(added))

        # Simple rename heuristic based on extension and name similarity
        matched_renames = set()

        for del_f in deleted_list:
            del_base = os.path.basename(del_f)
            for add_f in added_list:
                if add_f not in added: continue
                add_base = os.path.basename(add_f)
                if del_base == add_base: # Exact name match in different path
                    operators.append(SemanticOperator(
                        operator=OperatorType.RENAME_FILE,
                        file=add_f,
                        from_name=del_f,
                        to_name=add_f,
                        commit=commit_sha
                    ))
                    matched_renames.add((del_f, add_f))
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

    def _clean_body(self, text: str) -> str:
        """Helper to strip whitespace and comments for similarity comparison."""
        lines = []
        for line in text.splitlines():
            line = line.strip()
            # Remove comments (simple approximation)
            if line.startswith("#") or line.startswith("//"):
                continue
            if line:
                lines.append(line)
        return "\n".join(lines)

    def _compute_similarity(self, a: str, b: str) -> float:
        a_clean = self._clean_body(a)
        b_clean = self._clean_body(b)
        if not a_clean and not b_clean:
            return 1.0
        if not a_clean or not b_clean:
            return 0.0
        return difflib.SequenceMatcher(None, a_clean, b_clean).ratio()

    def _extract_function_ops(self, file: str, old_list: List[CodeSymbol], new_list: List[CodeSymbol], operators: List[SemanticOperator], commit: str):
        old_map = {s.name: s for s in old_list}
        new_map = {s.name: s for s in new_list}

        # Find potential renames
        deleted_names = set(old_map.keys()) - set(new_map.keys())
        added_names = set(new_map.keys()) - set(old_map.keys())

        matched_renames: Set[Tuple[str, str]] = set()
        
        # DSA: pre-calculate sorted lists to avoid repeated sorting in loops
        sorted_deleted = sorted(list(deleted_names))
        sorted_added = sorted(list(added_names))

        for del_name in sorted_deleted:
            del_sym = old_map[del_name]
            best_match: Optional[str] = None
            best_score = 0.0
            
            del_body_len = len(self._clean_body(del_sym.body))

            for add_name in sorted_added:
                # Need to check if still in added_names as it might have been removed by a previous match
                if add_name not in added_names:
                    continue
                    
                add_sym = new_map[add_name]
                # Filter matching by class context
                if del_sym.parent_class != add_sym.parent_class:
                    continue
                
                # HEURISTIC: Skip if body lengths are drastically different (>20% drift)
                add_body_len = len(self._clean_body(add_sym.body))
                if del_body_len > 0 and abs(del_body_len - add_body_len) / del_body_len > 0.2:
                    continue

                # Check text body similarity
                sim = self._compute_similarity(del_sym.body, add_sym.body)
                if sim > best_score:
                    best_score = sim
                    best_match = add_name

            if best_match and best_score >= self.rename_threshold:
                matched_renames.add((del_name, best_match))
                added_names.remove(best_match)
                deleted_names.remove(del_name)
                
                operators.append(SemanticOperator(
                    operator=OperatorType.RENAME_FUNCTION,
                    file=file,
                    commit=commit,
                    from_name=del_name,
                    to_name=best_match,
                    details={"similarity": round(best_score, 3), "parent_class": del_sym.parent_class}
                ))

        # Handle unmodified or modified functions
        common_names = sorted(list(set(old_map.keys()) & set(new_map.keys())))
        for name in common_names:
            old_sym = old_map[name]
            new_sym = new_map[name]

            # Check if signature or body changed
            sig_changed = old_sym.signature != new_sym.signature
            body_changed = self._clean_body(old_sym.body) != self._clean_body(new_sym.body)

            if sig_changed or body_changed:
                operators.append(SemanticOperator(
                    operator=OperatorType.MODIFY_FUNCTION,
                    file=file,
                    commit=commit,
                    name=name,
                    details={
                        "signature_changed": sig_changed,
                        "body_changed": body_changed,
                        "parent_class": old_sym.parent_class
                    }
                ))

        # Handle absolute deletes
        # DSA: reuse sorted_deleted but check current membership
        for name in sorted_deleted:
            if name in deleted_names:
                sym = old_map[name]
                operators.append(SemanticOperator(
                    operator=OperatorType.DELETE_FUNCTION,
                    file=file,
                    commit=commit,
                    name=name,
                    details={"parent_class": sym.parent_class}
                ))

        # Handle absolute additions
        # DSA: reuse sorted_added but check current membership
        for name in sorted_added:
            if name in added_names:
                sym = new_map[name]
                operators.append(SemanticOperator(
                    operator=OperatorType.ADD_FUNCTION,
                    file=file,
                    commit=commit,
                    name=name,
                    details={"parent_class": sym.parent_class}
                ))

    def _extract_class_ops(self, file: str, old_list: List[CodeSymbol], new_list: List[CodeSymbol], operators: List[SemanticOperator], commit: str):
        old_map = {s.name: s for s in old_list}
        new_map = {s.name: s for s in new_list}

        deleted_names = set(old_map.keys()) - set(new_map.keys())
        added_names = set(new_map.keys()) - set(old_map.keys())

        matched_renames: Set[Tuple[str, str]] = set()
        
        # DSA: pre-calculate sorted lists
        sorted_deleted = sorted(list(deleted_names))
        sorted_added = sorted(list(added_names))

        for del_name in sorted_deleted:
            del_sym = old_map[del_name]
            best_match: Optional[str] = None
            best_score = 0.0
            
            del_body_len = len(self._clean_body(del_sym.body))

            for add_name in sorted_added:
                # Need to check if still in added_names
                if add_name not in added_names:
                    continue
                    
                add_sym = new_map[add_name]
                
                # HEURISTIC: Skip if body lengths are drastically different (>20% drift)
                add_body_len = len(self._clean_body(add_sym.body))
                if del_body_len > 0 and abs(del_body_len - add_body_len) / del_body_len > 0.2:
                    continue

                sim = self._compute_similarity(del_sym.body, add_sym.body)
                if sim > best_score:
                    best_score = sim
                    best_match = add_name

            if best_match and best_score >= self.rename_threshold:
                matched_renames.add((del_name, best_match))
                added_names.remove(best_match)
                deleted_names.remove(del_name)

                operators.append(SemanticOperator(
                    operator=OperatorType.RENAME_CLASS,
                    file=file,
                    commit=commit,
                    from_name=del_name,
                    to_name=best_match,
                    details={"similarity": round(best_score, 3)}
                ))

        common_names = sorted(list(set(old_map.keys()) & set(new_map.keys())))
        for name in common_names:
            old_sym = old_map[name]
            new_sym = new_map[name]

            sig_changed = old_sym.signature != new_sym.signature
            body_changed = self._clean_body(old_sym.body) != self._clean_body(new_sym.body)

            if sig_changed or body_changed:
                operators.append(SemanticOperator(
                    operator=OperatorType.MODIFY_CLASS,
                    file=file,
                    commit=commit,
                    name=name,
                    details={
                        "signature_changed": sig_changed,
                        "body_changed": body_changed
                    }
                ))

        for name in sorted_deleted:
            if name in deleted_names:
                operators.append(SemanticOperator(
                    operator=OperatorType.DELETE_CLASS,
                    file=file,
                    commit=commit,
                    name=name
                ))

        for name in sorted_added:
            if name in added_names:
                operators.append(SemanticOperator(
                    operator=OperatorType.ADD_CLASS,
                    file=file,
                    commit=commit,
                    name=name
                ))

    def _extract_import_ops(self, file: str, old_list: List[CodeSymbol], new_list: List[CodeSymbol], operators: List[SemanticOperator], commit: str):
        # We track imports by module name
        old_modules = {s.module: s for s in old_list if s.module}
        new_modules = {s.module: s for s in new_list if s.module}

        old_keys = set(old_modules.keys())
        new_keys = set(new_modules.keys())

        deleted_imports = old_keys - new_keys
        added_imports = new_keys - old_keys
        common_imports = old_keys & new_keys

        # Check modifications of imported symbols for overlapping modules
        for mod in sorted(list(common_imports)):
            old_sym = old_modules[mod]
            new_sym = new_modules[mod]
            old_names = set(old_sym.imported_names)
            new_names = set(new_sym.imported_names)

            added_names = new_names - old_names
            removed_names = old_names - new_names

            if added_names or removed_names:
                # Detail the changes within the module
                operators.append(SemanticOperator(
                    operator=OperatorType.MODIFY_DEPENDENCY,
                    file=file,
                    commit=commit,
                    name=mod,
                    details={"added_names": list(added_names), "removed_names": list(removed_names)}
                ))

        for mod in sorted(list(deleted_imports)):
            sym = old_modules[mod]
            operators.append(SemanticOperator(
                operator=OperatorType.REMOVE_IMPORT,
                file=file,
                commit=commit,
                name=mod,
                details={"imported_names": sym.imported_names}
            ))

        for mod in sorted(list(added_imports)):
            sym = new_modules[mod]
            operators.append(SemanticOperator(
                operator=OperatorType.ADD_IMPORT,
                file=file,
                commit=commit,
                name=mod,
                details={"imported_names": sym.imported_names}
            ))
