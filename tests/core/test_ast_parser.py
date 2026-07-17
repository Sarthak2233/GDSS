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


def test_non_ascii_prefix_preserves_symbol_names():
    """Tree-sitter byte offsets must not corrupt names after multi-byte UTF-8."""
    code = """# café résumé 日本語 emoji 🚀
def process_payment(user):
    \"\"\"Handle payment for résumé.\"\"\"
    return user

class OrderService:
    def run(self):
        return process_payment("x")
"""
    parser = ASTParser()
    symbols = parser.parse_file("utf8_mod.py", content=code)

    funcs = [s for s in symbols if s.type == SymbolType.FUNCTION]
    classes = [s for s in symbols if s.type == SymbolType.CLASS]

    payment = next(f for f in funcs if f.name == "process_payment")
    assert payment.signature == "(user)"
    assert "return user" in payment.body

    assert len(classes) == 1
    assert classes[0].name == "OrderService"

    run_method = next(f for f in funcs if f.name == "run")
    assert run_method.parent_class == "OrderService"
    assert "process_payment" in run_method.calls


def test_parse_go_functions_and_structs():
    code = """
package main

func ProcessPayment(amount int) int {
    return amount
}

type Order struct {
    ID int
}
"""
    parser = ASTParser()
    symbols = parser.parse_file("pay.go", content=code)
    names = {s.name: s.type for s in symbols}
    assert "ProcessPayment" in names
    assert names["ProcessPayment"].value == "function"
    assert "Order" in names
    assert names["Order"].value == "class"


def test_content_hash_cache_returns_same_symbols():
    code = "def hello():\n    return 1\n"
    parser = ASTParser()
    first = parser.parse_file("cached.py", content=code)
    second = parser.parse_file("cached.py", content=code)
    assert first is second  # LRU content cache hit
    assert first[0].name == "hello"
