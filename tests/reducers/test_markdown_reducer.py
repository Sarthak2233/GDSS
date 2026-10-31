"""Unit tests for MarkdownSectionReducer (ATX heading extraction)."""

from __future__ import annotations

from gdss.core.transform_types import OperatorType
from gdss.reducers.markdown_reducer import MarkdownSectionReducer


def test_markdown_reducer_can_handle():
    reducer = MarkdownSectionReducer()
    assert reducer.can_handle("README.md")
    assert reducer.can_handle("docs/guide.markdown")
    assert reducer.can_handle("docs/spec.rst")
    assert not reducer.can_handle("server.py")


def test_markdown_section_addition():
    reducer = MarkdownSectionReducer()
    old_md = """# My Project\n\nIntro text."""
    new_md = """# My Project\n\nIntro text.\n\n## Features\n- Fast\n- Reliable"""

    ops = reducer.extract_operators("README.md", old_md, new_md)
    assert len(ops) == 1
    assert ops[0].operator == OperatorType.DOC_SECTION_APPEND
    assert ops[0].name == "doc::README.md#Features"


def test_markdown_section_content_modified():
    reducer = MarkdownSectionReducer()
    old_md = """# Title\n\n## Changelog\n- Item 1"""
    new_md = """# Title\n\n## Changelog\n- Item 1\n- Item 2 added by PR"""

    ops = reducer.extract_operators("CHANGELOG.md", old_md, new_md)
    assert len(ops) == 1
    assert ops[0].operator == OperatorType.DOC_SECTION_APPEND
    assert ops[0].name == "doc::CHANGELOG.md#Changelog"
