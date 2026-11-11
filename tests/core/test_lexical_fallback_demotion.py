"""Tests for Tier 3 fallback demotion to explicit lexical advisory mode (Ticket 02)."""

from __future__ import annotations

import logging

from gdss.core.ast_parser import ASTParser


def test_has_ast_grammar_and_is_supported():
    # Official registered Tree-sitter grammars
    assert ASTParser.has_ast_grammar(".cs") is True
    assert ASTParser.has_ast_grammar("cs") is True
    assert ASTParser.has_ast_grammar(".py") is True
    assert ASTParser.has_ast_grammar(".ts") is True
    assert ASTParser.has_ast_grammar(".js") is True
    assert ASTParser.has_ast_grammar(".go") is True
    assert ASTParser.has_ast_grammar(".rs") is True
    assert ASTParser.has_ast_grammar(".java") is True
    assert ASTParser.has_ast_grammar(".c") is True
    assert ASTParser.has_ast_grammar(".cpp") is True
    assert ASTParser.has_ast_grammar(".rb") is True
    assert ASTParser.has_ast_grammar(".sh") is True
    assert ASTParser.has_ast_grammar(".bash") is True

    # Languages without registered Tree-sitter grammar in current registry
    assert ASTParser.has_ast_grammar(".lua") is False
    assert ASTParser.has_ast_grammar(".sol") is False
    assert ASTParser.has_ast_grammar(".xyz") is False

    assert ASTParser.is_language_supported(".cs") is True
    assert ASTParser.is_language_supported(".xyz") is False


def test_lexical_advisory_flag_on_fallback_symbols(caplog):
    code = """
class LuaMockController
    function compute_hash(val)
        return val .. "_hash"
    end
end
"""
    parser = ASTParser()
    with caplog.at_level(logging.WARNING):
        symbols = parser.parse_file("controller.lua", content=code)

    # Verify warning was emitted
    assert any("No Tree-sitter grammar registered" in record.message for record in caplog.records)

    # Verify extracted symbols carry lexical advisory annotation
    assert len(symbols) >= 1
    for sym in symbols:
        assert sym.docstring == "lexical_advisory: true"

