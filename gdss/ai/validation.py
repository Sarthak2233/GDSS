"""Deterministic scope validation for proposed unified-diff patches."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from gdss.ai.types import Suggestion

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


@dataclass(frozen=True)
class PatchValidationResult:
    valid: bool
    reason: str | None = None


def _normalized_path(diff_path: str) -> str:
    prefix, _, path = diff_path.partition("/")
    return path if prefix in {"a", "b"} and path else diff_path


def validate_patch(suggestion: Suggestion, patch_text: str) -> PatchValidationResult:
    """Accept only one-file unified diffs whose changed ranges stay inside the anchor."""
    lines = patch_text.splitlines()
    old_paths = [line[4:] for line in lines if line.startswith("--- ")]
    new_paths = [line[4:] for line in lines if line.startswith("+++ ")]
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
