"""Sub-document region projection pipeline for hybrid multi-grammar source files.

Handles composite files like Blazor (.razor, .cshtml), Vue (.vue), and Svelte (.svelte)
by extracting embedded code regions and parsing them with true Tree-sitter AST visitors
while maintaining accurate parent document line and column coordinates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from gdss.core.transform_types import CodeSymbol
from gdss.logger import get_logger

if TYPE_CHECKING:
    from gdss.core.ast_parser import ASTParser

logger = get_logger("gdss.core.region_projector")

_RAZOR_CODE_BLOCK_RE = re.compile(r"@(code|functions)\s*\{", re.MULTILINE)
_VUE_SCRIPT_BLOCK_RE = re.compile(r"<script(?:\s+[^>]*)?>([\s\S]*?)<\/script>", re.IGNORECASE)
_SCRIPT_LANG_ATTR_RE = re.compile(r'lang\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)


@dataclass(frozen=True)
class ProjectedRegion:
    """A projected code segment with offset coordinates in its parent file."""

    language: str
    content: str
    start_line: int  # 1-indexed line in parent document
    start_column: int  # 1-indexed column in parent document
    synthetic_wrapper: bool = False


class RegionProjector:
    """Extracts embedded sub-document code regions and projects AST symbols."""

    @classmethod
    def can_project(cls, file_path: str) -> bool:
        """Return True if the file extension is a recognized hybrid document."""
        lower = file_path.lower()
        return (
            lower.endswith(".razor")
            or lower.endswith(".cshtml")
            or lower.endswith(".vue")
            or lower.endswith(".svelte")
        )

    @classmethod
    def extract_regions(cls, file_path: str, content: str) -> list[ProjectedRegion]:
        """Extract all embedded code regions from a hybrid document."""
        lower = file_path.lower()
        if lower.endswith(".razor") or lower.endswith(".cshtml"):
            return cls._extract_razor_regions(content)
        if lower.endswith(".vue") or lower.endswith(".svelte"):
            return cls._extract_vue_svelte_regions(content)
        return []

    @classmethod
    def _extract_razor_regions(cls, content: str) -> list[ProjectedRegion]:
        """Extract @code { ... } and @functions { ... } blocks from Razor documents."""
        regions: list[ProjectedRegion] = []

        for match in _RAZOR_CODE_BLOCK_RE.finditer(content):
            open_pos = match.end() - 1  # position of '{'
            # Balanced brace matching
            depth = 0
            close_pos = -1
            for idx in range(open_pos, len(content)):
                char = content[idx]
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        close_pos = idx
                        break

            if close_pos > open_pos:
                inner_code = content[open_pos + 1 : close_pos]
                preceding = content[: open_pos + 1]
                start_line = preceding.count("\n") + 1

                # Wrap in synthetic partial class so C# parser recognizes members
                wrapped = f"public partial class __RazorComponent {{\n{inner_code}\n}}"
                regions.append(
                    ProjectedRegion(
                        language="c_sharp",
                        content=wrapped,
                        start_line=start_line - 1,  # accounting for synthetic wrapper line
                        start_column=1,
                        synthetic_wrapper=True,
                    )
                )

        return regions

    @classmethod
    def _extract_vue_svelte_regions(cls, content: str) -> list[ProjectedRegion]:
        """Extract <script> blocks from Vue / Svelte SFCs."""
        regions: list[ProjectedRegion] = []

        for match in _VUE_SCRIPT_BLOCK_RE.finditer(content):
            full_tag = match.group(0)
            inner_code = match.group(1)

            # Determine language
            lang_match = _SCRIPT_LANG_ATTR_RE.search(full_tag)
            lang_attr = lang_match.group(1).lower().strip() if lang_match else ""
            language = "typescript" if lang_attr in {"ts", "tsx", "typescript"} else "javascript"

            # Calculate start line of inner code
            tag_open_end = match.start(1)
            preceding = content[:tag_open_end]
            start_line = preceding.count("\n") + 1

            regions.append(
                ProjectedRegion(
                    language=language,
                    content=inner_code,
                    start_line=start_line,
                    start_column=1,
                    synthetic_wrapper=False,
                )
            )

        return regions

    @classmethod
    def project_and_parse(
        cls,
        file_path: str,
        content: str,
        ast_parser: ASTParser,
    ) -> list[CodeSymbol]:
        """Extract regions, parse via Tree-sitter, and map coordinates back to parent."""
        regions = cls.extract_regions(file_path, content)
        all_symbols: list[CodeSymbol] = []

        for region in regions:
            # Parse inner content with matching pseudo-filename
            ext = ".cs" if region.language == "c_sharp" else ".ts"
            pseudo_name = f"__projected_region{ext}"
            raw_symbols = ast_parser.parse_file(pseudo_name, content=region.content)

            line_delta = region.start_line

            for sym in raw_symbols:
                # Discard synthetic wrapper class if present
                if region.synthetic_wrapper and sym.name == "__RazorComponent":
                    continue

                # Project start/end lines
                sym.start_line = max(1, sym.start_line + line_delta)
                sym.end_line = max(1, sym.end_line + line_delta)
                sym.chart_location = file_path
                sym.language = region.language

                if sym.parent_class == "__RazorComponent":
                    sym.parent_class = None

                for block in sym.body_blocks:
                    block.start_line = max(1, block.start_line + line_delta)
                    block.end_line = max(1, block.end_line + line_delta)

                sym.ensure_identity(file_path)
                all_symbols.append(sym)

        return all_symbols

