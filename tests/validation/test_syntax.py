"""Tests for gdss.validation.syntax (Multi-language AST Syntax Validator)."""
from __future__ import annotations

from gdss.validation.syntax import validate_file_syntax, validate_source_syntax


def test_validate_python_syntax_valid():
    code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    res = validate_source_syntax(code, "math.py")
    assert res.valid is True
    assert res.language == "python"
    assert res.error_message is None


def test_validate_python_syntax_invalid():
    code = "def add(a, b:\n    return a + b\n"
    res = validate_source_syntax(code, "math.py")
    assert res.valid is False
    assert res.language == "python"
    assert res.line_number is not None
    assert res.error_message is not None


def test_validate_typescript_syntax_valid():
    code = "export function multiply(x: number, y: number): number {\n  return x * y;\n}\n"
    res = validate_source_syntax(code, "math.ts")
    assert res.valid is True
    assert res.language == "typescript"


def test_validate_typescript_syntax_invalid():
    code = "export function multiply(x: number, {\n  return x * y;\n"
    res = validate_source_syntax(code, "math.ts")
    assert res.valid is False
    assert res.language == "typescript"
    assert res.error_message is not None


def test_validate_file_syntax_on_disk(tmp_path):
    py_file = tmp_path / "valid.py"
    py_file.write_text("x = [1, 2, 3]\n", encoding="utf-8")
    assert validate_file_syntax(py_file).valid is True

    bad_file = tmp_path / "broken.py"
    bad_file.write_text("x = [1, 2,\n", encoding="utf-8")
    res = validate_file_syntax(bad_file)
    assert res.valid is False
    assert res.line_number is not None


def test_validate_unknown_extension_fallback():
    code = "(module (func (export \"main\")))"
    res = validate_source_syntax(code, "module.wat")
    # For unsupported language without registered parser, passes with informative status
    assert res.valid is True
    assert res.language == "unknown"
