import pytest
from gdss.core.ast_parser import ASTParser
from gdss.core.transform_types import SymbolType

def test_parse_python_code():
    code = """
import os
from math import sin, cos

class Calculator:
    \"\"\"A simple calculator class.\"\"\"
    def add(self, a, b):
        return a + b

def global_helper():
    res = Calculator().add(1, 2)
    return res
"""
    parser = ASTParser()
    symbols = parser.parse_file("test.py", content=code)

    # Filter symbols
    imports = [s for s in symbols if s.type == SymbolType.IMPORT]
    classes = [s for s in symbols if s.type == SymbolType.CLASS]
    funcs = [s for s in symbols if s.type == SymbolType.FUNCTION]

    # Verify imports
    assert len(imports) == 2
    assert imports[0].module == "os"
    assert imports[1].module == "math"
    assert "sin" in imports[1].imported_names
    assert "cos" in imports[1].imported_names

    # Verify classes
    assert len(classes) == 1
    assert classes[0].name == "Calculator"

    # Verify functions
    assert len(funcs) == 2
    
    # Method add inside Calculator
    add_method = next(f for f in funcs if f.name == "add")
    assert add_method.parent_class == "Calculator"
    assert "a, b" in add_method.signature

    # Global function global_helper
    helper_func = next(f for f in funcs if f.name == "global_helper")
    assert helper_func.parent_class is None
    # Statically resolved call to 'add'
    assert "add" in helper_func.calls

def test_parse_javascript_code():
    code = """
import { helper } from './utils';

class Payment {
    process(amount) {
        helper();
        return true;
    }
}

function calculateTax(subtotal) {
    return subtotal * 0.15;
}
"""
    parser = ASTParser()
    symbols = parser.parse_file("test.js", content=code)

    imports = [s for s in symbols if s.type == SymbolType.IMPORT]
    classes = [s for s in symbols if s.type == SymbolType.CLASS]
    funcs = [s for s in symbols if s.type == SymbolType.FUNCTION]

    assert len(imports) == 1
    assert imports[0].module == "./utils"
    assert "helper" in imports[0].imported_names

    assert len(classes) == 1
    assert classes[0].name == "Payment"

    assert len(funcs) == 2
    process_method = next(f for f in funcs if f.name == "process")
    assert process_method.parent_class == "Payment"
    assert "helper" in process_method.calls

    tax_func = next(f for f in funcs if f.name == "calculateTax")
    assert tax_func.parent_class is None
