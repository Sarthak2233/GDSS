"""Universal Lexical Fallback Reducer for any arbitrary or unrecognized repository file."""

from __future__ import annotations

import difflib

from gdss.core.transform_types import OperatorType, SemanticOperator
from gdss.logger import get_logger

logger = get_logger("gdss.reducers.lexical")


_CHUNK_TAGS = frozenset({"replace", "delete", "insert"})


class UniversalLexicalReducer:
    """Fallback line-range diff chunk reducer guaranteeing zero false negatives on arbitrary files."""

    def can_handle(self, file_path: str, content: str | None = None) -> bool:
        _ = (file_path, content)
        return True

    def extract_operators(
        self,
        file_path: str,
        old_content: str | None,
        new_content: str | None,
        commit_sha: str = "",
    ) -> list[SemanticOperator]:
        old_lines = (old_content or "").splitlines()
        new_lines = (new_content or "").splitlines()
        new_count = len(new_lines)

        if old_content is None and new_content is not None:
            return [
                SemanticOperator(
                    operator=OperatorType.LEXICAL_CHUNK_EDIT,
                    file=file_path,
                    commit=commit_sha,
                    name=f"lexical::{file_path}",
                    details={"line_start": 1, "line_end": new_count, "kind": "added"},
                    symbol_id=f"lexical::{file_path}:1-{new_count}",
                )
            ]

        if old_content is not None and new_content is None:
            old_count = len(old_lines)
            return [
                SemanticOperator(
                    operator=OperatorType.LEXICAL_CHUNK_EDIT,
                    file=file_path,
                    commit=commit_sha,
                    name=f"lexical::{file_path}",
                    details={"line_start": 1, "line_end": old_count, "kind": "deleted"},
                    symbol_id=f"lexical::{file_path}:deleted",
                )
            ]

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        operators: list[SemanticOperator] = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag in _CHUNK_TAGS:
                operators.append(
                    SemanticOperator(
                        operator=OperatorType.LEXICAL_CHUNK_EDIT,
                        file=file_path,
                        commit=commit_sha,
                        name=f"lexical::{file_path}",
                        details={
                            "tag": tag,
                            "line_start": j1 + 1,
                            "line_end": max(j1 + 1, j2),
                            "old_range": (i1 + 1, i2),
                        },
                        symbol_id=f"lexical::{file_path}:{j1 + 1}-{max(j1 + 1, j2)}",
                    )
                )

        return operators
