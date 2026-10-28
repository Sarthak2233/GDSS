"""Deterministic scope and syntax validation for proposed unified-diff patches and replacement blocks."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from gdss.ai.patch_parser import clean_markdown_fence, replacement_to_unified_diff
from gdss.ai.types import Suggestion
from gdss.core.ast_parser import ASTParser

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


@dataclass(frozen=True)
class PatchValidationResult:
    valid: bool
    reason: str | None = None
    synthesized_diff: str | None = None


def _normalized_path(diff_path: str) -> str:
    prefix, _, path = diff_path.partition("/")
    return path if prefix in {"a", "b"} and path else diff_path


def _validate_replacement_syntax(code: str, file_path: str) -> tuple[bool, str | None]:
    """Validate syntax of replacement code block using native ast or tree-sitter."""
    ext = PurePosixPath(file_path).suffix.lower()
    if ext == ".py":
        try:
            ast.parse(code, filename=file_path)
            return True, None
        except SyntaxError as exc:
            msg = f"{exc.msg} at line {exc.lineno}" if exc.lineno else str(exc)
            return False, f"Python syntax error: {msg}"
        except Exception as exc:
            return False, f"Python parse error: {exc}"

    # For other languages, use tree-sitter parser if available
    try:
        parser = ASTParser.get_parser_for_ext(ext)
        if parser:
            tree = parser.parse(code.encode("utf-8"))
            if tree.root_node.has_error:
                return False, f"Syntax error in {ext} code block"
    except Exception:
        pass

    return True, None


def validate_patch(
    suggestion: Suggestion,
    patch_text: str,
    original_code: str | None = None,
) -> PatchValidationResult:
    """Validate patch text: accepts unified diffs (constrained to anchor) or clean replacement blocks (syntax verified)."""
    cleaned = clean_markdown_fence(patch_text).strip()
    if not cleaned:
        return PatchValidationResult(False, "patch text is empty")

    lines = cleaned.splitlines()
    old_paths = [line[4:].strip() for line in lines if line.startswith("--- ")]
    new_paths = [line[4:].strip() for line in lines if line.startswith("+++ ")]

    # Case A: Standard Unified Diff
    if old_paths and new_paths:
        if len(old_paths) != 1 or len(new_paths) != 1:
            return PatchValidationResult(False, "patch must contain exactly one file")

        target = str(PurePosixPath(suggestion.file_path))
        if _normalized_path(old_paths[0]) != target or _normalized_path(new_paths[0]) != target:
            return PatchValidationResult(False, "patch targets a file outside the approved anchor")

        hunks = [match for line in lines if (match := _HUNK_RE.match(line))]
        if not hunks:
            return PatchValidationResult(False, "patch has no unified-diff hunks")

        for hunk in hunks:
            old_start = int(hunk.group(1))
            old_count = int(hunk.group(2) or "1")
            new_start = int(hunk.group(3))
            new_count = int(hunk.group(4) or "1")
            start = min(old_start, new_start)
            end = max(old_start + max(1, old_count) - 1, new_start + max(1, new_count) - 1)
            if start < suggestion.line_start or end > suggestion.line_end:
                return PatchValidationResult(False, "patch hunk is outside the approved symbol range")

        return PatchValidationResult(True)

    # Case B: Clean Replacement Code Block
    syntax_ok, syntax_err = _validate_replacement_syntax(cleaned, suggestion.file_path)
    if not syntax_ok:
        return PatchValidationResult(False, syntax_err or "syntax validation failed")

    # If original code is provided, synthesize a unified diff for validation sandbox & apply
    synthesized: str | None = None
    if original_code is not None:
        try:
            synthesized = replacement_to_unified_diff(
                cleaned,
                original_code,
                suggestion.file_path,
                suggestion.line_start,
                suggestion.line_end,
            )
        except Exception:
            synthesized = None

    return PatchValidationResult(True, synthesized_diff=synthesized)
