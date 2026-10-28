"""Base protocol and abstractions for Domain Reducers."""

from __future__ import annotations

from typing import Protocol

from gdss.core.transform_types import SemanticOperator


class DomainReducer(Protocol):
    """Protocol for specialized domain file reduction."""

    def can_handle(self, file_path: str, content: str | None = None) -> bool:
        """Return True if this reducer is specialized for the given file or content signature."""
        ...

    def extract_operators(
        self,
        file_path: str,
        old_content: str | None,
        new_content: str | None,
        commit_sha: str = "",
    ) -> list[SemanticOperator]:
        """Extract domain-specific SemanticOperators comparing old and new states."""
        ...
