"""Strict parser for model-produced, named strategy patch sections."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import PurePosixPath

_HEADER_RE = re.compile(
    r"^--- patch: (?P<path>[^:\n]+):(?P<start>\d+)-(?P<end>\d+) "
    r"\(strategy: (?P<strategy>[^)]+)\) ---$"
)
_END_MARKER = "--- end ---"
_MAX_RESPONSE_BYTES = 200_000


class PatchParseError(ValueError):
    """Safe parser failure that intentionally excludes model response content."""


def _safe_path(path: str) -> bool:
    normalized = PurePosixPath(path)
    return not normalized.is_absolute() and ".." not in normalized.parts


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
        if not body or not body[0].startswith("--- "):
            raise PatchParseError("patch section does not contain a unified diff")
        patches[strategy] = "\n".join(body) + "\n"
        index += 1

    missing = expected - patches.keys()
    if missing:
        raise PatchParseError("model response is missing one or more requested strategies")
    return patches
