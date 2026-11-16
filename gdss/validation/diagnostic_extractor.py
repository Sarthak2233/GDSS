"""Closed-Loop Validation Diagnostics & Anti-Gaming Invariant Extractor (Phase 2).

Extracts structured diagnostic traces (tracebacks, assertion comparisons, implicated symbols)
from sandbox test and typecheck executions, distinguishes patch-introduced regressions from
pre-existing baseline failures, and enforces anti-gaming invariants on test assertions.
Runs strictly on local CPU with zero tokens and zero external API dependencies.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any

from gdss.logger import get_logger

logger = get_logger("gdss.validation.diagnostic")

# Regex patterns for Pytest short summary info and failure blocks
_PYTEST_FAILED_RE = re.compile(
    r"^FAILED\s+([^:]+)::([^\s\-]+)(?:\s+-\s+(.*))?$",
    re.MULTILINE,
)
_LINE_ERR_RE = re.compile(r"^([^:\n]+):(\d+):\s+([A-Za-z0-9_]+)", re.MULTILINE)
_ASSERT_EQ_RE = re.compile(r"assert\s+([^\n=]+?)\s*==\s*([^\n]+)")
_SYMBOL_IDENT_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]{2,})\b")

# Multi-language runner patterns
_CARGO_PANIC_RE = re.compile(
    r"thread '([^']+)' panicked at (?:'([^']+)', )?([^:\n]+):(\d+):(\d+)"
)
_CARGO_LEFT_RIGHT_RE = re.compile(
    r"left:\s*`?([^\n`]+?)`?(?:,\s*|\s*\n\s*)right:\s*`?([^\n`]+)`?"
)

_VITEST_FAIL_RE = re.compile(
    r"(?:FAIL|✖)\s+([^\s\n]+\.(?:ts|tsx|js|jsx|mjs|cjs))\s*>\s*([^\n]+)",
    re.MULTILINE,
)
_VITEST_ASSERT_RE = re.compile(
    r"expected\s+([^\n]+?)\s+to\s+(?:deeply\s+equal|equal|be)\s+([^\n/]+)",
    re.IGNORECASE,
)
_LINE_VITEST_RE = re.compile(r"❯\s+([^:\n]+):(\d+):(\d+)")

_GOTEST_FAIL_RE = re.compile(
    r"---\s+FAIL:\s+([A-Za-z0-9_]+)\s+\([^\)]+\)",
    re.MULTILINE,
)
_GOTEST_LINE_RE = re.compile(
    r"^\s+([^:\n]+\.go):(\d+):\s*(.*)$",
    re.MULTILINE,
)

_DOTNET_FAIL_RE = re.compile(
    r"Failed\s+([A-Za-z0-9_\.]+)\s+\[[0-9\s\w]+\]", re.MULTILINE
)
_DOTNET_EXPECTED_RE = re.compile(r"Expected:\s+([^\n]+)")
_DOTNET_ACTUAL_RE = re.compile(r"Actual:\s+([^\n]+)")
_DOTNET_LINE_RE = re.compile(r"in\s+([^:\n]+):line\s+(\d+)")

# Multi-language test assertion patterns
_LANG_ASSERTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "rust": re.compile(r"\b(assert!|assert_eq!|assert_ne!|debug_assert!|debug_assert_eq!)"),
    "go": re.compile(
        r"\b(assert\.[A-Za-z0-9_]+|require\.[A-Za-z0-9_]+|t\.(?:Error|Fatal|Fail)[A-Za-z0-9_]*)\b"
    ),
    "typescript": re.compile(r"\b(expect\b|assert\b|\.toBe\(|\.toEqual\(|\.to\.equal\()"),
    "javascript": re.compile(r"\b(expect\b|assert\b|\.toBe\(|\.toEqual\(|\.to\.equal\()"),
    "csharp": re.compile(r"\b(Assert\.[A-Za-z0-9_]+|should\.[A-Za-z0-9_]+)\b"),
    "java": re.compile(r"\b(assert[A-Z][A-Za-z0-9_]*|assertThat|assertAll)\b"),
}

_TRIVIAL_ASSERTION_PATTERNS = re.compile(
    r"(?:"
    r"assert!\s*\(\s*true\s*\)|"
    r"assert\.True\s*\([^,\)]+,\s*true\s*\)|"
    r"expect\s*\(\s*true\s*\)\.toBe\s*\(\s*true\s*\)|"
    r"Assert\.True\s*\(\s*true\s*\)|"
    r"assertTrue\s*\(\s*true\s*\)"
    r")",
    re.IGNORECASE,
)


@dataclass
class DiagnosticEvidence:
    """Structured diagnostic failure information for a single test failure."""

    test_file: str
    test_case: str
    failure_type: str = "UnknownError"
    expected: str | None = None
    actual: str | None = None
    line_number: int | None = None
    traceback: list[str] = field(default_factory=list)
    implicated_symbols: list[str] = field(default_factory=list)
    regression_origin: str = "INTRODUCED_BY_PATCH"  # INTRODUCED_BY_PATCH | PRE_EXISTING_BASELINE

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_file": self.test_file,
            "test_case": self.test_case,
            "failure_type": self.failure_type,
            "expected": self.expected,
            "actual": self.actual,
            "line_number": self.line_number,
            "traceback": self.traceback,
            "implicated_symbols": self.implicated_symbols,
            "regression_origin": self.regression_origin,
        }


@dataclass
class DiagnosticPayload:
    """The aggregate structured diagnostic report from a validation execution."""

    status: str  # "PASS", "VALIDATION_FAILED", "SYNTAX_FAILED", "TYPE_FAILED"
    total_failed: int
    tool: str
    diagnostics: list[DiagnosticEvidence] = field(default_factory=list)
    raw_output: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "total_failed": self.total_failed,
            "tool": self.tool,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }


@dataclass(frozen=True)
class AntiGamingCheckResult:
    """Evaluation result of whether a test file diff complies with anti-gaming invariants."""

    passed: bool
    deleted_assertions_count: int
    modified_assertions_count: int
    warnings: list[str] = field(default_factory=list)


def parse_test_diagnostics(
    tool_name: str,
    raw_output: str,
    exit_code: int = 1,
) -> DiagnosticPayload:
    """Parse raw runner stdout/stderr into structured diagnostic evidence ($E_k$)."""
    if exit_code == 0:
        return DiagnosticPayload(
            status="PASS",
            total_failed=0,
            tool=tool_name,
            diagnostics=[],
            raw_output=raw_output,
        )

    diagnostics: list[DiagnosticEvidence] = []
    output_lines = raw_output.splitlines()

    # 1. Parse Pytest format
    pytest_matches = list(_PYTEST_FAILED_RE.finditer(raw_output))
    if pytest_matches:
        for match in pytest_matches:
            test_file = match.group(1).strip()
            test_case = match.group(2).strip()
            full_msg = (match.group(3) or "").strip()

            expected: str | None = None
            actual: str | None = None
            line_no: int | None = None
            implicated: list[str] = []

            if ":" in full_msg and not full_msg.startswith("assert"):
                parts = full_msg.split(":", 1)
                failure_type = parts[0].strip()
                detail = parts[1].strip()
            elif "assert" in full_msg:
                failure_type = "AssertionError"
                detail = full_msg
            else:
                failure_type = full_msg or "AssertionError"
                detail = full_msg

            # Check if detail is an assertion comparison (e.g. assert 50 == 100)
            if "assert" in detail:
                failure_type = "AssertionError"
                eq_match = _ASSERT_EQ_RE.search(detail)
                if eq_match:
                    actual = eq_match.group(1).strip()
                    expected = eq_match.group(2).strip()
            elif failure_type in {"TypeError", "NameError", "AttributeError"}:
                expected = detail

            # Scan traceback / failure lines for line number and implicated symbols
            implicated_seen: set[str] = set()
            for line in output_lines:
                pytest_line_m = _LINE_ERR_RE.search(line)
                if pytest_line_m:
                    m_file = pytest_line_m.group(1)
                    if test_file in m_file or m_file in raw_output:
                        try:
                            py_line_val = pytest_line_m.group(2)
                            line_no = int(py_line_val)  # dsa:ignore
                        except ValueError:
                            pass
                if line.startswith(">") or line.startswith("E "):
                    # Extract function/symbol names from failing code line
                    words = _SYMBOL_IDENT_RE.findall(line)
                    for w in words:
                        if (
                            w not in {"def", "assert", "self", "return", "True", "False", "None"}
                            and w not in implicated_seen
                        ):
                            implicated_seen.add(w)
                            implicated.append(w)

            evidence = DiagnosticEvidence(
                test_file=test_file,
                test_case=test_case,
                failure_type=failure_type,
                expected=expected,
                actual=actual,
                line_number=line_no,
                traceback=[
                    line_str
                    for line_str in output_lines
                    if line_str.startswith("E ") or line_str.startswith(">")
                ][:10],
                implicated_symbols=implicated[:5],
                regression_origin="INTRODUCED_BY_PATCH",
            )
            diagnostics.append(evidence)

    # 2. Parse Vitest / Jest (TypeScript / JavaScript)
    if not diagnostics and ("vitest" in tool_name or "npm" in tool_name or "jest" in tool_name or "FAIL" in raw_output):
        vitest_matches = list(_VITEST_FAIL_RE.finditer(raw_output))
        for vm in vitest_matches:
            test_file = vm.group(1).strip()
            raw_case = vm.group(2).strip()
            parts = [p.strip() for p in raw_case.split(">") if p.strip()]
            test_case = parts[-1] if parts else raw_case
            actual = None
            expected = None
            line_no = None

            assert_m = _VITEST_ASSERT_RE.search(raw_output)
            if assert_m:
                actual = assert_m.group(1).strip()
                expected = assert_m.group(2).strip()

            vitest_line_m = _LINE_VITEST_RE.search(raw_output)
            if vitest_line_m:
                try:
                    vt_line_str = vitest_line_m.group(2)
                    line_no = int(vt_line_str)
                except ValueError:
                    pass

            evidence = DiagnosticEvidence(
                test_file=test_file,
                test_case=test_case,
                failure_type="AssertionError",
                expected=expected,
                actual=actual,
                line_number=line_no,
                regression_origin="INTRODUCED_BY_PATCH",
            )
            diagnostics.append(evidence)

    # 3. Parse Cargo (Rust) format
    if not diagnostics and ("cargo" in tool_name or "rust" in tool_name or "panicked at" in raw_output):
        cargo_matches = list(_CARGO_PANIC_RE.finditer(raw_output))
        for cm in cargo_matches:
            test_case = cm.group(1).strip()
            panic_msg = cm.group(2) or ""
            test_file = cm.group(3).strip()
            cm_line = cm.group(4)
            line_no = int(cm_line) if cm_line else None

            actual = None
            expected = None
            lr_m = _CARGO_LEFT_RIGHT_RE.search(raw_output)
            if lr_m:
                actual = lr_m.group(1).strip()
                expected = lr_m.group(2).strip()

            evidence = DiagnosticEvidence(
                test_file=test_file,
                test_case=test_case,
                failure_type="PanicAssertionFailure",
                expected=expected or panic_msg,
                actual=actual,
                line_number=line_no,
                regression_origin="INTRODUCED_BY_PATCH",
            )
            diagnostics.append(evidence)

    # 4. Parse Go test format
    if not diagnostics and ("go" in tool_name or "--- FAIL:" in raw_output):
        go_matches = list(_GOTEST_FAIL_RE.finditer(raw_output))
        line_matches = list(_GOTEST_LINE_RE.finditer(raw_output))
        for gm in go_matches:
            test_case = gm.group(1).strip()
            test_file = "test.go"
            line_no = None
            msg = ""
            if line_matches:
                first_line = line_matches[0]
                test_file = first_line.group(1).strip()
                line_no = int(first_line.group(2))
                msg = first_line.group(3).strip()

            evidence = DiagnosticEvidence(
                test_file=test_file,
                test_case=test_case,
                failure_type="TestFailure",
                expected=msg,
                line_number=line_no,
                regression_origin="INTRODUCED_BY_PATCH",
            )
            diagnostics.append(evidence)

    # 5. Parse .NET (C#) format
    if not diagnostics and ("dotnet" in tool_name or "csharp" in tool_name or "Assert.Equal() Failure" in raw_output):
        dotnet_matches = list(_DOTNET_FAIL_RE.finditer(raw_output))
        for dm in dotnet_matches:
            test_case = dm.group(1).strip()
            actual = None
            expected = None
            line_no = None
            test_file = "Tests.cs"

            exp_m = _DOTNET_EXPECTED_RE.search(raw_output)
            if exp_m:
                expected = exp_m.group(1).strip()
            act_m = _DOTNET_ACTUAL_RE.search(raw_output)
            if act_m:
                actual = act_m.group(1).strip()
            dotnet_line_m = _DOTNET_LINE_RE.search(raw_output)
            if dotnet_line_m:
                test_file = dotnet_line_m.group(1).strip()
                try:
                    dotnet_line_val = dotnet_line_m.group(2)
                    line_no = int(dotnet_line_val)
                except ValueError:
                    pass

            evidence = DiagnosticEvidence(
                test_file=test_file,
                test_case=test_case,
                failure_type="AssertFailure",
                expected=expected,
                actual=actual,
                line_number=line_no,
                regression_origin="INTRODUCED_BY_PATCH",
            )
            diagnostics.append(evidence)

    # 6. Generic fallback if tool output was not matched by specific parser
    if not diagnostics:
        evidence = DiagnosticEvidence(
            test_file="generic",
            test_case="suite",
            failure_type="ValidationFailure",
            expected=raw_output.strip()[:300],
            regression_origin="INTRODUCED_BY_PATCH",
        )
        diagnostics.append(evidence)

    return DiagnosticPayload(
        status="VALIDATION_FAILED",
        total_failed=len(diagnostics),
        tool=tool_name,
        diagnostics=diagnostics,
        raw_output=raw_output,
    )


def compute_differential_diagnostics(
    candidate_diag: DiagnosticPayload,
    baseline_diag: DiagnosticPayload | None,
) -> DiagnosticPayload:
    """Compare candidate diagnostics against pre-flight baseline failures.

    Isolates INTRODUCED_BY_PATCH from PRE_EXISTING_BASELINE failures.
    """
    if not baseline_diag or not baseline_diag.diagnostics:
        return candidate_diag

    baseline_set = {(b.test_file, b.test_case) for b in baseline_diag.diagnostics}

    updated_diagnostics: list[DiagnosticEvidence] = []
    for d in candidate_diag.diagnostics:
        key = (d.test_file, d.test_case)
        if key in baseline_set:
            d.regression_origin = "PRE_EXISTING_BASELINE"
        else:
            d.regression_origin = "INTRODUCED_BY_PATCH"
        updated_diagnostics.append(d)

    return DiagnosticPayload(
        status=candidate_diag.status,
        total_failed=len(updated_diagnostics),
        tool=candidate_diag.tool,
        diagnostics=updated_diagnostics,
        raw_output=candidate_diag.raw_output,
    )


def inspect_test_diff_anti_gaming(
    original_content: str,
    patched_content: str,
    file_path: str = "",
    strict: bool = True,
    allow_callsite_updates: bool = True,
) -> AntiGamingCheckResult:
    """Enforce the Test Anti-Gaming Invariant on a modified test file.

    Guarantees that an AI convergence assistant cannot game the validation
    gate by deleting or trivializing test assertions.

    Args:
        original_content: Test file text prior to patch application.
        patched_content: Test file text after patch application.
        file_path: Relative path to the test file.
        strict: If True (default), any deleted assertion fails the gate. If False,
            deleted assertions produce warnings but pass if no trivializations occurred.
        allow_callsite_updates: If True (default), adapts caller signatures without penalty.
    """
    warnings: list[str] = []
    deleted_count = 0
    modified_count = 0

    norm_path = file_path.lower()
    is_python = norm_path.endswith((".py", ".pyi")) or "python" in norm_path
    python_analyzed = False

    # Fast path for Python test files using AST analysis
    if is_python:
        try:
            orig_tree = ast.parse(original_content)
            patch_tree = ast.parse(patched_content)

            def count_assertions(tree: ast.AST) -> tuple[int, int]:
                assert_count = 0
                trivial_count = 0
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assert):
                        assert_count += 1
                        # Check for trivial assertions like `assert True` or `assert 1`
                        if isinstance(node.test, ast.Constant) and bool(node.test.value) is True:
                            trivial_count += 1
                    elif isinstance(node, ast.Call):
                        # Check self.assert* in unittest
                        func = node.func
                        if isinstance(func, ast.Attribute) and func.attr.startswith("assert"):
                            assert_count += 1
                            if func.attr in {"assertTrue", "assertEqual"}:
                                if node.args and isinstance(node.args[0], ast.Constant):
                                    if bool(node.args[0].value) is True:
                                        trivial_count += 1
                return assert_count, trivial_count

            orig_total, orig_trivial = count_assertions(orig_tree)
            patch_total, patch_trivial = count_assertions(patch_tree)

            if patch_total < orig_total:
                deleted_count = orig_total - patch_total
                warnings.append(
                    f"ANTI_GAMING_WARNING: {deleted_count} assertion(s) were removed or deleted from test file '{file_path}'"
                )

            if patch_trivial > orig_trivial:
                modified_count = patch_trivial - orig_trivial
                warnings.append(
                    f"ANTI_GAMING_WARNING: {modified_count} assertion(s) were trivialized (e.g. 'assert True') in test file '{file_path}'"
                )

            python_analyzed = True
        except Exception as exc:
            logger.debug("AST parsing failed for Python anti-gaming check (%s): %s", file_path, exc)

    # Multi-language lexical analysis (Rust, Go, TypeScript/JavaScript, C#, Java, C/C++)
    if not python_analyzed:
        lang = "generic"
        if norm_path.endswith((".ts", ".tsx", ".js", ".jsx", ".mjs")):
            lang = "typescript"
        elif norm_path.endswith(".rs"):
            lang = "rust"
        elif norm_path.endswith(".go"):
            lang = "go"
        elif norm_path.endswith((".cs", ".csx")):
            lang = "csharp"
        elif norm_path.endswith(".java"):
            lang = "java"

        pattern = _LANG_ASSERTION_PATTERNS.get(lang)
        if not pattern:
            pattern = re.compile(r"\b(assert\b|expect\b|self\.assert|Assert\.)")

        orig_asserts = len(pattern.findall(original_content))
        patch_asserts = len(pattern.findall(patched_content))

        if patch_asserts < orig_asserts:
            deleted_count = orig_asserts - patch_asserts
            warnings.append(
                f"ANTI_GAMING_WARNING: {deleted_count} {lang} assertion pattern(s) removed from test file '{file_path}'"
            )

        # Check for trivialized assertions across languages
        orig_trivial = len(_TRIVIAL_ASSERTION_PATTERNS.findall(original_content))
        patch_trivial = len(_TRIVIAL_ASSERTION_PATTERNS.findall(patched_content))
        if patch_trivial > orig_trivial:
            modified_count = patch_trivial - orig_trivial
            warnings.append(
                f"ANTI_GAMING_WARNING: {modified_count} trivial assertion pattern(s) detected in test file '{file_path}'"
            )

    if strict:
        passed = (deleted_count == 0 and modified_count == 0)
    else:
        # Non-strict mode: deleted assertions trigger warnings but do not fail the gate;
        # trivialized assertions (e.g. assert True) always fail.
        passed = (modified_count == 0)

    return AntiGamingCheckResult(
        passed=passed,
        deleted_assertions_count=deleted_count,
        modified_assertions_count=modified_count,
        warnings=warnings,
    )
