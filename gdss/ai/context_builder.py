"""3-Way semantic collision context extractor.

Extracts the complete semantic triangle (V_base, V_A, V_B) along with
AST symbol boundaries, impacted caller graphs, and context-window budgeting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

from gdss.ai.condensation import condense_block, get_model_code_budget
from gdss.ai.types import Suggestion
from gdss.core.ast_parser import ASTParser
from gdss.core.transform_types import CodeSymbol, OperatorType, SemanticOperator
from gdss.drift.context import AnalysisContext
from gdss.logger import get_logger

logger = get_logger("gdss.ai.context_builder")


@dataclass(frozen=True)
class SemanticCollisionContext:
    """Complete 3-way semantic representation of a collision."""

    file_path: str
    symbol_name: str
    language: str
    base_branch: str
    base_code: str
    base_line_range: tuple[int, int] | None
    branch_a_name: str
    branch_a_code: str
    branch_a_line_range: tuple[int, int] | None
    branch_b_name: str
    branch_b_code: str
    branch_b_line_range: tuple[int, int] | None
    impacted_callers: tuple[str, ...] = field(default_factory=tuple)
    extra_context: dict[str, Any] = field(default_factory=dict)


def _clean_symbol_name(symbol_id: str) -> str:
    """Extract bare symbol name from qualified symbol ID (e.g. 'path/file.py::func' -> 'func')."""
    if "::" in symbol_id:
        return symbol_id.rsplit("::", 1)[-1]
    return symbol_id.strip()


def _detect_language_from_path(file_path: str) -> str:
    """Deduce language name from file extension."""
    ext = PurePosixPath(file_path).suffix.lower()
    mapping = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
    }
    return mapping.get(ext, "python")


def _find_symbol_in_symbols(
    symbols: list[CodeSymbol],
    symbol_name: str,
) -> CodeSymbol | None:
    """Find symbol by exact name, qualified name, or method name."""
    if not symbols:
        return None

    # Exact match on symbol.name
    for sym in symbols:
        if sym.name == symbol_name:
            return sym

    # Check method match (e.g. Class.method or ParentClass::method)
    clean_target = symbol_name.split(".")[-1].split("::")[-1]
    for sym in symbols:
        if sym.name == clean_target:
            return sym

    # Check parent_class.name
    for sym in symbols:
        if sym.parent_class and f"{sym.parent_class}.{sym.name}" == symbol_name:
            return sym

    return None


def _extract_symbol_from_branch(
    context: AnalysisContext,
    branch_ref: str,
    file_path: str,
    symbol_name: str,
    parser: ASTParser,
    fallback_line_range: tuple[int, int] | None = None,
) -> tuple[str, tuple[int, int] | None, str]:
    """Extract symbol code, line range, and detected language at a specific Git ref."""
    detected_lang = _detect_language_from_path(file_path)
    if not branch_ref:
        return "", None, detected_lang

    content: str | None = None
    if context.observer:
        try:
            content = context.observer.get_file_content_at_commit(branch_ref, file_path)
        except Exception as exc:
            logger.debug(
                "Failed to retrieve file content at ref '%s' for '%s': %s",
                branch_ref,
                file_path,
                exc,
            )

    if not content:
        return "", None, detected_lang

    lines = content.splitlines(keepends=True)
    num_lines = len(lines)

    symbols = parser.parse_file(file_path, content=content)
    matched_sym = _find_symbol_in_symbols(symbols, symbol_name)

    if matched_sym:
        start = max(1, matched_sym.start_line)
        end = min(num_lines, matched_sym.end_line)
        code = "".join(lines[start - 1 : end])
        return code, (start, end), getattr(matched_sym, "language", detected_lang)

    # Fallback to anchor line range if symbol lookup did not match
    if fallback_line_range:
        f_start, f_end = fallback_line_range
        if 1 <= f_start <= num_lines:
            end = min(num_lines, f_end)
            code = "".join(lines[f_start - 1 : end])
            return code, (f_start, end), detected_lang

    return "", None, detected_lang


def _find_impacted_callers(
    context: AnalysisContext,
    symbol_name: str,
    branch_a: str,
    branch_b: str,
) -> tuple[str, ...]:
    """Find callers and contractual references across branches."""
    callers: list[str] = []

    # Check semantic operators
    dep_op_types = {
        OperatorType.ADD_DEPENDENCY,
        OperatorType.REMOVE_DEPENDENCY,
        OperatorType.MODIFY_DEPENDENCY,
    }
    relevant_branches = [b for b in (branch_a, branch_b) if b]
    for b in relevant_branches:
        for op in context.branch_operators.get(b, ()):
            if not isinstance(op, SemanticOperator):
                continue
            is_dep_op = op.operator in dep_op_types
            op_target = op.get_target_name() or ""
            details_to = str(op.details.get("to") or "")
            if is_dep_op and (symbol_name in op_target or symbol_name in details_to):
                callers.append(
                    f"{b}: {op.operator.value} in {op.file} ({op.name} -> {details_to})"
                )
            elif symbol_name in op_target and op.file != "":
                callers.append(f"{b}: {op.operator.value} on {op.file}::{op_target}")

    return tuple(sorted(set(callers)))


def _condense_code_block(
    code: str,
    budget: int,
    context: AnalysisContext,
    suggestion: Suggestion,
) -> str:
    """Condense code block to fit within character budget, preserving signature and structure."""
    if len(code) <= budget:
        return code

    # Try AST-aware child omission first
    try:
        condensed = condense_block(context, suggestion, code, max_chars=budget)
    except Exception:
        condensed = code

    condensed_len = len(condensed)
    if condensed_len <= budget:
        return condensed

    # If still exceeding budget, perform structured head/tail condensation
    lines = condensed.splitlines(keepends=True)
    num_lines = len(lines)
    if num_lines > 20:
        head_count = max(8, num_lines // 4)
        tail_count = max(5, num_lines // 6)
        omission_comment = "    # ... [unmodified code omitted to fit context budget] ...\n"
        trimmed_lines = lines[:head_count] + [omission_comment] + lines[-tail_count:]
        candidate = "".join(trimmed_lines)
        candidate_len = len(candidate)
        if candidate_len < condensed_len:
            condensed = candidate
            condensed_len = candidate_len

    # Hard cap if still over budget
    if condensed_len > budget and budget > 100:
        half = (budget - 80) // 2
        condensed = condensed[:half] + "\n    # ... [truncated] ...\n" + condensed[-half:]

    return condensed


def extract_3way_symbol_context(
    context: AnalysisContext,
    suggestion: Suggestion,
    other_branch: str | None = None,
    *,
    model_name: str | None = None,
    provider: Any | None = None,
    max_code_chars: int | None = None,
) -> SemanticCollisionContext:
    """Extract full 3-way semantic representation: Base ($V_{base}$), Branch A ($V_A$), Branch B ($V_B$)."""
    file_path = suggestion.file_path
    symbol_name = _clean_symbol_name(suggestion.symbol_id)

    base_branch = context.reference_branch
    branch_a = (
        suggestion.anchor.target_branch
        if suggestion.anchor and suggestion.anchor.target_branch
        else (suggestion.context.candidate_branch if suggestion.context else "HEAD")
    )
    branch_b = (
        other_branch
        or (suggestion.context.other_branch if suggestion.context else "")
        or ""
    )

    parser = context.parser if getattr(context, "parser", None) else ASTParser()

    # Anchor fallback line range for Branch A
    anchor_range = (
        (suggestion.anchor.line_start, suggestion.anchor.line_end)
        if suggestion.anchor
        else (suggestion.line_start, suggestion.line_end)
    )

    # 1. Base definition ($V_{base}$)
    base_code, base_range, base_lang = _extract_symbol_from_branch(
        context,
        base_branch,
        file_path,
        symbol_name,
        parser,
        fallback_line_range=None,
    )

    # 2. Branch A definition ($V_A$)
    a_code, a_range, a_lang = _extract_symbol_from_branch(
        context,
        branch_a,
        file_path,
        symbol_name,
        parser,
        fallback_line_range=anchor_range,
    )

    # 3. Branch B definition ($V_B$)
    b_code, b_range, b_lang = _extract_symbol_from_branch(
        context,
        branch_b,
        file_path,
        symbol_name,
        parser,
        fallback_line_range=None,
    )

    detected_lang = a_lang or b_lang or base_lang or _detect_language_from_path(file_path)

    # Context window budgeting and condensation
    budget = max_code_chars
    if budget is None or budget <= 0:
        budget = get_model_code_budget(model_name, provider=provider)

    per_block_budget = max(budget // 3, 100) if budget < 6000 else max(budget // 3, 2000)

    base_code = _condense_code_block(base_code, per_block_budget, context, suggestion)
    a_code = _condense_code_block(a_code, per_block_budget, context, suggestion)
    b_code = _condense_code_block(b_code, per_block_budget, context, suggestion)

    # Impacted callers across branches
    callers = _find_impacted_callers(context, symbol_name, branch_a, branch_b)

    return SemanticCollisionContext(
        file_path=file_path,
        symbol_name=symbol_name,
        language=detected_lang,
        base_branch=base_branch,
        base_code=base_code,
        base_line_range=base_range,
        branch_a_name=branch_a,
        branch_a_code=a_code,
        branch_a_line_range=a_range,
        branch_b_name=branch_b,
        branch_b_code=b_code,
        branch_b_line_range=b_range,
        impacted_callers=callers,
    )
