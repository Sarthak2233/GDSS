"""Semantic Reducer for Markdown and documentation assets."""

from __future__ import annotations

import re
from typing import Any

from gdss.core.transform_types import OperatorType, SemanticOperator
from gdss.logger import get_logger

logger = get_logger("gdss.reducers.markdown")

_HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<title>.+)$", re.MULTILINE)


class MarkdownSectionReducer:
    """Extracts section-level operators from Markdown files."""

    def can_handle(self, file_path: str, content: str | None = None) -> bool:
        lower = file_path.lower()
        if lower.endswith((".md", ".markdown", ".rst")):
            return True
        if content and content.startswith("# "):
            return True
        return False

    def extract_operators(
        self,
        file_path: str,
        old_content: str | None,
        new_content: str | None,
        commit_sha: str = "",
    ) -> list[SemanticOperator]:
        old_sections = self._parse_sections(old_content or "")
        new_sections = self._parse_sections(new_content or "")

        operators: list[SemanticOperator] = []
        all_titles = set(old_sections.keys()) | set(new_sections.keys())

        for title in sorted(all_titles):
            old_sec = old_sections.get(title)
            new_sec = new_sections.get(title)

            clean_title = re.sub(r"[^\w\- ]", "", title).strip().replace(" ", "-")
            symbol_id = f"doc::{file_path}#{clean_title}"

            if old_sec is None and new_sec is not None:
                operators.append(
                    SemanticOperator(
                        operator=OperatorType.DOC_SECTION_APPEND,
                        file=file_path,
                        commit=commit_sha,
                        name=f"doc::{file_path}#{title}",
                        details={"title": title, "level": new_sec.get("level", 1)},
                        symbol_id=symbol_id,
                    )
                )
            elif old_sec is not None and new_sec is not None:
                # Content changed under this section
                if old_sec.get("content", "").strip() != new_sec.get("content", "").strip():
                    operators.append(
                        SemanticOperator(
                            operator=OperatorType.DOC_SECTION_APPEND,
                            file=file_path,
                            commit=commit_sha,
                            name=f"doc::{file_path}#{title}",
                            details={"title": title, "level": new_sec.get("level", 1)},
                            symbol_id=symbol_id,
                        )
                    )

        return operators

    def _parse_sections(self, content: str) -> dict[str, dict[str, Any]]:
        sections: dict[str, dict[str, Any]] = {}
        lines = content.splitlines()
        current_title: str | None = None
        current_level = 1
        current_lines: list[str] = []

        for line in lines:
            m = re.match(r"^(?P<hashes>#{1,6})\s+(?P<title>.+)$", line)
            if m:
                if current_title:
                    sections[current_title] = {
                        "level": current_level,
                        "content": "\n".join(current_lines),
                    }
                current_title = m.group("title").strip()
                current_level = len(m.group("hashes"))
                current_lines = []
            else:
                if current_title:
                    current_lines.append(line)

        if current_title:
            sections[current_title] = {
                "level": current_level,
                "content": "\n".join(current_lines),
            }

        return sections
