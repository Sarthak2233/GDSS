#!/usr/bin/env python3
"""GDSS DSA fitness sensor (computational, deterministic).

Scans the Python source files under ``gdss/`` for common DSA anti-patterns:
1. Linear membership tests (e.g., ``x in some_list``).
2. Nested loops over the same collection (O(N^2) complexity).
3. NetworkX graph reverse copy (e.g., ``g.reverse(copy=True)``).
4. Repeated function calls with identical arguments inside a function/method.
5. Dict-building via append + search (e.g., ``if x not in list_var: list_var.append(x)``).

Violations can be suppressed using a '# dsa:ignore' comment on the offending line.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "gdss"


class DSAChecker(ast.NodeVisitor):
    def __init__(self, filename: str, lines: list[str]):
        self.filename = filename
        self.lines = lines
        self.violations: list[tuple[int, str, str, str]] = []  # lineno, what, why, fix
        # Track variables assigned to list literals, list comprehensions, or list() in the current scope
        self.list_variables: set[str] = set()
        self.current_function: str | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Save current state for nested functions
        old_list_vars = self.list_variables.copy()
        old_func = self.current_function
        self.current_function = node.name
        self.list_variables = set()

        # Track repeated calls in this function
        self._check_repeated_calls(node)

        self.generic_visit(node)

        # Restore state
        self.list_variables = old_list_vars
        self.current_function = old_func

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        # Same as FunctionDef
        old_list_vars = self.list_variables.copy()
        old_func = self.current_function
        self.current_function = node.name
        self.list_variables = set()

        self._check_repeated_calls(node)

        self.generic_visit(node)

        self.list_variables = old_list_vars
        self.current_function = old_func

    def visit_Assign(self, node: ast.Assign):
        # Track assignments to list types
        is_list = False
        if isinstance(node.value, (ast.List, ast.ListComp)):
            is_list = True
        elif isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
            if node.value.func.id in ("list", "tuple"):
                is_list = True

        if is_list:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.list_variables.add(target.id)

        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare):
        # Check 1: Linear membership test
        for op in node.ops:
            if isinstance(op, (ast.In, ast.NotIn)):
                for comp in node.comparators:
                    # Direct list literal or tuple literal
                    if isinstance(comp, (ast.List, ast.Tuple)):
                        self._add_violation(
                            node.lineno,
                            "Linear membership test with literal list/tuple",
                            "Checking membership ('in' / 'not in') against a list/tuple literal takes O(N) time.",
                            "Convert the literal to a set (e.g., using '{...}') for O(1) average lookup time."
                        )
                    # Variable known to be a list
                    elif isinstance(comp, ast.Name) and comp.id in self.list_variables:
                        # Skip if it's named 'calls' or something that is small or handled
                        self._add_violation(
                            node.lineno,
                            f"Linear membership test on list variable '{comp.id}'",
                            f"Checking membership on the list variable '{comp.id}' takes O(N) time.",
                            f"Convert '{comp.id}' to a set (or use a set for membership queries) for O(1) lookup."
                        )
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        # Check 2: Nested loops over same collection
        # Look for nested For loops in node.body
        for child in ast.walk(node):
            if child is node:
                continue
            if isinstance(child, ast.For):
                # Check if they iterate over the same variable name
                outer_iter = self._get_name_id(node.iter)
                inner_iter = self._get_name_id(child.iter)
                if outer_iter and inner_iter and outer_iter == inner_iter:
                    self._add_violation(
                        child.lineno,
                        f"Nested loops over the same collection '{outer_iter}'",
                        f"Iterating over '{outer_iter}' inside an outer loop iterating over the same collection leads to O(N^2) time complexity.",
                        "Use a hash map (dict) or set to lookup elements in O(1) time instead of performing nested iterations."
                    )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # Check 3: Graph reverse copy
        # Look for g.reverse(copy=True)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "reverse":
            for kw in node.keywords:
                if kw.arg == "copy":
                    val = self._get_constant_val(kw.value)
                    if val is True:
                        self._add_violation(
                            node.lineno,
                            "NetworkX graph reverse copy",
                            "Calling '.reverse(copy=True)' copies the entire graph, which is highly inefficient for large graphs.",
                            "Use '.reverse(copy=False)' to return a read-only view of the reversed graph without copying memory."
                        )
        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        # Check 5: Dict-building via append + search
        # Detect if x not in list_var: list_var.append(x)
        if isinstance(node.test, ast.Compare) and len(node.test.ops) == 1:
            op = node.test.ops[0]
            if isinstance(op, ast.NotIn) and len(node.test.comparators) == 1:
                comp = node.test.comparators[0]
                if isinstance(comp, ast.Name):
                    list_name = comp.id
                    # Now check the body for append to list_name
                    for body_node in node.body:
                        if isinstance(body_node, ast.Expr) and isinstance(body_node.value, ast.Call):
                            call = body_node.value
                            if isinstance(call.func, ast.Attribute) and call.func.attr == "append":
                                obj_name = self._get_name_id(call.func.value)
                                if obj_name == list_name:
                                    self._add_violation(
                                        node.lineno,
                                        f"O(N^2) list-building via check-and-append on '{list_name}'",
                                        f"Checking membership in '{list_name}' before appending inside a loop results in quadratic O(N^2) time complexity.",
                                        "Use a set to keep track of seen items, or use a dict/set directly."
                                    )
        self.generic_visit(node)

    def _check_repeated_calls(self, func_node: ast.FunctionDef | ast.AsyncFunctionDef):
        # Walk function body and find repeated ast.Call nodes that are identical
        call_counts: dict[str, list[ast.Call]] = {}
        for child in ast.walk(func_node):
            if isinstance(child, ast.Call):
                # Avoid side-effecting calls or very common builtins
                func_str = self._call_to_str(child)
                if func_str and not self._is_side_effecting(func_str):
                    call_counts.setdefault(func_str, []).append(child)

        for func_str, calls in call_counts.items():
            if len(calls) > 1:
                # We have repeated calls to the same function/method with same args
                # Report on the second and subsequent call lines
                for dup_call in calls[1:]:
                    self._add_violation(
                        dup_call.lineno,
                        f"Repeated function call '{func_str}' in function '{func_node.name}'",
                        f"Calling '{func_str}' multiple times in the same function computes the same result repeatedly.",
                        "Assign the result to a local variable or cache it using '@functools.lru_cache'."
                    )

    def _call_to_str(self, node: ast.Call) -> str | None:
        """Returns a string representation of the call if it contains only basic names/literals."""
        func_name = self._node_to_str(node.func)
        if not func_name:
            return None
        args_reprs = []
        for arg in node.args:
            arg_repr = self._node_to_str(arg)
            if arg_repr is None:
                return None  # complex arg, skip
            args_reprs.append(arg_repr)

        for kw in node.keywords:
            kw_val_repr = self._node_to_str(kw.value)
            if kw_val_repr is None:
                return None
            args_reprs.append(f"{kw.arg}={kw_val_repr}")

        return f"{func_name}({', '.join(args_reprs)})"

    def _node_to_str(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            val = self._node_to_str(node.value)
            if val:
                return f"{val}.{node.attr}"
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        return None

    def _is_side_effecting(self, func_str: str) -> bool:
        # Common side-effecting function/method names or O(1) dict/string helpers to ignore
        parts = func_str.split("(")[0].split(".")
        name = parts[-1]
        return name in (
            "append", "add", "remove", "pop", "insert", "update", "extend",
            "write", "print", "debug", "info", "warning", "error", "log",
            "add_node", "add_edge", "remove_node", "remove_nodes_from", "remove_edges_from",
            # O(1) dict operations
            "keys", "values", "items", "get",
            # Basic string/path operations
            "startswith", "endswith", "split", "strip", "lower", "upper", "join",
            "is_dir", "exists", "read_text", "relative_to", "get_node_text"
        )

    def _get_name_id(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        return None

    def _get_constant_val(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        return None

    def _add_violation(self, lineno: int, what: str, why: str, fix: str):
        # Check if the line has '# dsa:ignore'
        if 1 <= lineno <= len(self.lines):
            line_content = self.lines[lineno - 1]
            if "dsa:ignore" in line_content:
                return  # suppressed
        self.violations.append((lineno, what, why, fix))


def check_file(path: Path, baseline: dict[str, list[dict[str, any]]]) -> list[str]:
    violations: list[str] = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines()
        tree = ast.parse(content)
    except SyntaxError as exc:
        violations.append(
            f"WHAT: {path.relative_to(ROOT)} failed to parse (line {exc.lineno}).\n"
            f"  WHY: the DSA fitness sensor cannot analyze unparsable code.\n"
            f"  FIX: fix the syntax error: {exc.msg}"
        )
        return violations
    except Exception as exc:
        violations.append(
            f"WHAT: {path.relative_to(ROOT)} failed to read.\n"
            f"  WHY: {exc}\n"
            f"  FIX: check file permissions and existence."
        )
        return violations

    checker = DSAChecker(str(path), lines)
    checker.visit(tree)

    rel = str(path.relative_to(ROOT))
    file_baseline = baseline.get(rel, [])

    for lineno, what, why, fix in checker.violations:
        # Check if violation is in the baseline
        is_baselined = False
        for item in file_baseline:
            if item.get("lineno") == lineno and item.get("what") == what:
                is_baselined = True
                break

        if not is_baselined:
            violations.append(
                f"WHAT: {rel}:{lineno} - {what}\n"
                f"  WHY: {why}\n"
                f"  FIX: {fix}"
            )

    return violations


def load_baseline() -> dict[str, list[dict[str, any]]]:
    import json
    baseline_path = Path(__file__).resolve().parent / "dsa_baseline.json"
    if baseline_path.is_file():
        try:
            return json.loads(baseline_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def main() -> int:
    import json
    # Determine if we should generate/update the baseline
    generate_baseline = "--generate-baseline" in sys.argv

    baseline = {} if generate_baseline else load_baseline()
    violations: list[str] = []

    all_raw_violations: dict[str, list[dict[str, any]]] = {}

    if PKG.is_dir():
        for py in sorted(PKG.rglob("*.py")):
            if generate_baseline:
                try:
                    content = py.read_text(encoding="utf-8", errors="ignore")
                    lines = content.splitlines()
                    tree = ast.parse(content)
                    checker = DSAChecker(str(py), lines)
                    checker.visit(tree)
                    if checker.violations:
                        rel = str(py.relative_to(ROOT))
                        all_raw_violations[rel] = [
                            {"lineno": lineno, "what": what, "why": why, "fix": fix}
                            for lineno, what, why, fix in checker.violations
                        ]
                except Exception:
                    pass
            else:
                violations.extend(check_file(py, baseline))

    if generate_baseline:
        baseline_path = Path(__file__).resolve().parent / "dsa_baseline.json"
        baseline_path.write_text(json.dumps(all_raw_violations, indent=2), encoding="utf-8")
        print(f"Generated DSA baseline with {sum(len(v) for v in all_raw_violations.values())} violations at {baseline_path}")
        return 0

    if violations:
        print("DSA fitness check: FAIL", file=sys.stderr)
        for v in violations:
            print("- " + v, file=sys.stderr)
        print(
            f"\n{len(violations)} DSA violation(s) found. See "
            ".cursor/rules/35-dsa-optimization.mdc for guidelines.\n"
            "You can suppress warnings with a '# dsa:ignore' comment on the offending line or update the baseline.",
            file=sys.stderr,
        )
        return 1
    print("DSA fitness check: OK (no unsuppressed DSA violations found).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
