"""Strict parser and multi-format bridge for model-produced patches and replacement blocks."""

from __future__ import annotations

import difflib
import re
from collections.abc import Sequence
from pathlib import PurePosixPath
from typing import Literal

_HEADER_RE = re.compile(
    r"^--- patch: (?P<path>[^:\n]+):(?P<start>\d+)-(?P<end>\d+) "
    r"\(strategy: (?P<strategy>[^)]+)\) ---$"
)
_END_MARKER = "--- end ---"
_MAX_RESPONSE_BYTES = 200_000
_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class PatchParseError(ValueError):
    """Safe parser failure that intentionally excludes model response content."""


def _safe_path(path: str) -> bool:
    normalized = PurePosixPath(path)
    return not normalized.is_absolute() and ".." not in normalized.parts


def clean_markdown_fence(text: str) -> str:
    """Strip markdown code fence wrappers (e.g. ```diff ... ``` or ```python ... ```)."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def replacement_to_unified_diff(
    replacement_code: str,
    original_code: str,
    file_path: str,
    line_start: int,
    line_end: int = 0,
) -> str:
    """Synthesize a standard Unified Diff from a clean replacement code block.

    Translates line offsets to align precisely with the target symbol anchor.
    """
    _ = line_end  # Preserved for anchor boundary interface compatibility
    clean_rep = clean_markdown_fence(replacement_code)
    orig_lines = original_code.splitlines(keepends=True)
    rep_lines = clean_rep.splitlines(keepends=True)

    # Ensure trailing newlines for diff accuracy
    if orig_lines and not orig_lines[-1].endswith("\n"):
        orig_lines[-1] += "\n"
    if rep_lines and not rep_lines[-1].endswith("\n"):
        rep_lines[-1] += "\n"

    diff_lines = list(
        difflib.unified_diff(
            orig_lines,
            rep_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            n=2,
        )
    )

    if not diff_lines:
        return ""

    offset = max(0, line_start - 1)
    adjusted_diff_lines: list[str] = []
    for line in diff_lines:
        m = _HUNK_RE.match(line)
        if m:
            old_start = int(m.group(1)) + offset
            old_count = m.group(2)
            new_start = int(m.group(3)) + offset
            new_count = m.group(4)
            old_part = f"{old_start},{old_count}" if old_count else str(old_start)
            new_part = f"{new_start},{new_count}" if new_count else str(new_start)
            adjusted_diff_lines.append(f"@@ -{old_part} +{new_part} @@\n")
        else:
            adjusted_diff_lines.append(line if line.endswith("\n") else line + "\n")

    return "".join(adjusted_diff_lines)


def extract_patch_or_replacement(
    response: str,
    expected_file: str | None = None,
) -> tuple[str, Literal["unified_diff", "replacement_block"]]:
    """Inspect model response and extract either a Unified Diff or a clean replacement block."""
    cleaned = clean_markdown_fence(response).strip()
    if not cleaned:
        return "", "replacement_block"

    # Check if it has unified diff headers
    lines = cleaned.splitlines()
    has_diff_headers = any(line.startswith("--- ") for line in lines) and any(
        line.startswith("+++ ") for line in lines
    )
    indexed_lines = list(enumerate(lines))
    if has_diff_headers:
        # Extract starting from first '--- ' line
        start_idx = next(i for i, line in indexed_lines if line.startswith("--- "))
        diff_text = "\n".join(lines[start_idx:]).strip() + "\n"
        return diff_text, "unified_diff"

    # If it contains @@ hunk headers without ---/+++, synthesize diff headers with expected_file
    if any(line.startswith("@@ ") for line in lines):
        hunk_start = next(i for i, line in indexed_lines if line.startswith("@@ "))
        hunks = "\n".join(lines[hunk_start:]).strip() + "\n"
        target = expected_file or "patch.diff"
        return f"--- a/{target}\n+++ b/{target}\n{hunks}", "unified_diff"

    return cleaned, "replacement_block"


def parse_strategy_patches(
    response: str,
    *,
    expected_strategies: Sequence[str],
    max_response_bytes: int = _MAX_RESPONSE_BYTES,
) -> dict[str, str]:
    """Parse exactly one unified-diff section for each requested strategy."""
    if len(response.encode("utf-8")) > max_response_bytes:
        raise PatchParseError("model response exceeds the configured size limit")
    expected = set(expected_strategies)
    if not expected:
        raise PatchParseError("at least one expected strategy is required")

    patches: dict[str, str] = {}
    lines = response.splitlines()
    num_lines = len(lines)
    err_missing_end = PatchParseError("patch section is missing its end marker")
    index = 0
    while index < num_lines:
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        header = _HEADER_RE.match(line)
        if header is None:
            raise PatchParseError("model response contains content outside a named patch section")
        path = header.group("path")
        strategy = header.group("strategy")
        if not _safe_path(path):
            raise PatchParseError("patch section uses an unsafe path")
        if strategy not in expected:
            raise PatchParseError("patch section uses an unrequested strategy")
        if strategy in patches:
            raise PatchParseError("model response contains a duplicate strategy")

        index += 1
        body: list[str] = []
        while index < num_lines and lines[index] != _END_MARKER:
            if _HEADER_RE.match(lines[index]):
                raise err_missing_end
            body.append(lines[index])
            index += 1
        if index == num_lines:
            raise err_missing_end

        # Strip accidental markdown code block fences if present inside section
        while body and body[0].startswith("```"):
            body = body[1:]
        while body and body[-1].strip() == "```":
            body = body[:-1]

        if not body or not body[0].startswith("--- "):
            raise PatchParseError("patch section does not contain a unified diff")
        patches[strategy] = "\n".join(body) + "\n"
        index += 1

    missing = expected - patches.keys()
    if missing:
        raise PatchParseError("model response is missing one or more requested strategies")
    return patches
