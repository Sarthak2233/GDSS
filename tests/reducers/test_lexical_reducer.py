"""Unit tests for UniversalLexicalReducer (line-level fallback for arbitrary files)."""

from __future__ import annotations

from gdss.core.transform_types import OperatorType
from gdss.reducers.lexical_reducer import UniversalLexicalReducer


def test_lexical_reducer_can_handle_anything():
    reducer = UniversalLexicalReducer()
    assert reducer.can_handle(".env")
    assert reducer.can_handle("Dockerfile")
    assert reducer.can_handle(".github/workflows/ci.yml")
    assert reducer.can_handle("custom.conf")


def test_lexical_reducer_extracts_changed_lines():
    reducer = UniversalLexicalReducer()
    old_content = "NODE_ENV=development\nPORT=3000\nDEBUG=true\n"
    new_content = "NODE_ENV=development\nPORT=8080\nDEBUG=true\n"

    ops = reducer.extract_operators(".env", old_content, new_content)
    assert len(ops) == 1
    assert ops[0].operator == OperatorType.LEXICAL_CHUNK_EDIT
    assert ops[0].name == "lexical::.env"
    assert ops[0].file == ".env"
    assert ops[0].details.get("line_start") is not None


def test_lexical_reducer_added_file():
    reducer = UniversalLexicalReducer()
    new_content = "FROM node:20-alpine\nWORKDIR /app\n"

    ops = reducer.extract_operators("Dockerfile", None, new_content)
    assert len(ops) == 1
    assert ops[0].operator == OperatorType.LEXICAL_CHUNK_EDIT
    assert ops[0].name == "lexical::Dockerfile"
