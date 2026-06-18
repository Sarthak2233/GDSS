import pytest
from gdss.core.transform_types import CodeSymbol, SymbolType, OperatorType
from gdss.core.transform_extractor import TransformExtractor

def test_extract_function_operators():
    extractor = TransformExtractor()

    # Original state
    old_symbols = [
        CodeSymbol(name="process_payment", type=SymbolType.FUNCTION, start_line=5, end_line=10, signature="(user, card)", body="def process_payment(user, card):\n    validate_card()\n    execute_payment()"),
        CodeSymbol(name="unmodified_helper", type=SymbolType.FUNCTION, start_line=12, end_line=14, signature="()", body="def unmodified_helper():\n    pass"),
        CodeSymbol(name="to_be_deleted", type=SymbolType.FUNCTION, start_line=16, end_line=18, signature="()", body="def to_be_deleted():\n    print('goodbye')")
    ]

    # New state (with process_payment renamed to execute_payment, a new function added, one deleted, and helper unmodified)
    new_symbols = [
        CodeSymbol(name="execute_payment", type=SymbolType.FUNCTION, start_line=5, end_line=10, signature="(user, card)", body="def execute_payment(user, card):\n    validate_card()\n    execute_payment()"),
        CodeSymbol(name="unmodified_helper", type=SymbolType.FUNCTION, start_line=12, end_line=14, signature="()", body="def unmodified_helper():\n    pass"),
        CodeSymbol(name="newly_added", type=SymbolType.FUNCTION, start_line=20, end_line=22, signature="()", body="def newly_added():\n    print('hello')")
    ]

    operators = extractor.extract_operators("billing.py", old_symbols, new_symbols)

    # We expect: RENAME_FUNCTION (process_payment -> execute_payment), DELETE_FUNCTION (to_be_deleted), ADD_FUNCTION (newly_added)
    renames = [op for op in operators if op.operator == OperatorType.RENAME_FUNCTION]
    deletes = [op for op in operators if op.operator == OperatorType.DELETE_FUNCTION]
    adds = [op for op in operators if op.operator == OperatorType.ADD_FUNCTION]
    modifies = [op for op in operators if op.operator == OperatorType.MODIFY_FUNCTION]

    assert len(renames) == 1
    assert renames[0].from_name == "process_payment"
    assert renames[0].to_name == "execute_payment"

    assert len(deletes) == 1
    assert deletes[0].name == "to_be_deleted"

    assert len(adds) == 1
    assert adds[0].name == "newly_added"

    assert len(modifies) == 0

def test_modify_function_operators():
    extractor = TransformExtractor()

    old_symbols = [
        CodeSymbol(name="calculate_tax", type=SymbolType.FUNCTION, start_line=5, end_line=8, signature="(subtotal)", body="def calculate_tax(subtotal):\n    return subtotal * 0.1")
    ]

    new_symbols = [
        CodeSymbol(name="calculate_tax", type=SymbolType.FUNCTION, start_line=5, end_line=8, signature="(subtotal, rate=0.15)", body="def calculate_tax(subtotal, rate=0.15):\n    return subtotal * rate")
    ]

    operators = extractor.extract_operators("tax.py", old_symbols, new_symbols)

    modifies = [op for op in operators if op.operator == OperatorType.MODIFY_FUNCTION]
    assert len(modifies) == 1
    assert modifies[0].name == "calculate_tax"
    assert modifies[0].details["signature_changed"] is True
    assert modifies[0].details["body_changed"] is True
