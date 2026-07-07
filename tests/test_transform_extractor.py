import pytest
from gdss.core.transform_types import CodeSymbol, SymbolType, OperatorType, SemanticOperator
from gdss.core.transform_extractor import TransformExtractor
from gdss.core.structural_fingerprint import normalized_similarity, levenshtein_distance


def test_extract_function_operators():
    extractor = TransformExtractor()

    old_symbols = [
        CodeSymbol(
            name="process_payment",
            type=SymbolType.FUNCTION,
            start_line=5,
            end_line=10,
            signature="(user, card)",
            body="def process_payment(user, card):\n    validate_card()\n    execute_payment()",
            structural_tokens=["expression_statement", "expression_statement"],
        ),
        CodeSymbol(
            name="unmodified_helper",
            type=SymbolType.FUNCTION,
            start_line=12,
            end_line=14,
            signature="()",
            body="def unmodified_helper():\n    pass",
            structural_tokens=["pass_statement"],
        ),
        CodeSymbol(
            name="to_be_deleted",
            type=SymbolType.FUNCTION,
            start_line=16,
            end_line=18,
            signature="()",
            body="def to_be_deleted():\n    pass",
            structural_tokens=["pass_statement"],
        ),
    ]

    new_symbols = [
        CodeSymbol(
            name="execute_payment",
            type=SymbolType.FUNCTION,
            start_line=5,
            end_line=10,
            signature="(user, card)",
            body="def execute_payment(user, card):\n    validate_card()\n    execute_payment()",
            structural_tokens=["expression_statement", "expression_statement"],
        ),
        CodeSymbol(
            name="unmodified_helper",
            type=SymbolType.FUNCTION,
            start_line=12,
            end_line=14,
            signature="()",
            body="def unmodified_helper():\n    pass",
            structural_tokens=["pass_statement"],
        ),
        CodeSymbol(
            name="newly_added",
            type=SymbolType.FUNCTION,
            start_line=20,
            end_line=22,
            signature="()",
            body="def newly_added():\n    print('hello')",
            structural_tokens=["expression_statement"],
        ),
    ]

    operators = extractor.extract_operators("billing.py", old_symbols, new_symbols)

    renames = [op for op in operators if op.operator == OperatorType.RENAME_FUNCTION]
    deletes = [op for op in operators if op.operator == OperatorType.DELETE_FUNCTION]
    adds = [op for op in operators if op.operator == OperatorType.ADD_FUNCTION]
    modifies = [op for op in operators if op.operator == OperatorType.MODIFY_FUNCTION]

    assert len(renames) == 1
    assert renames[0].from_name == "process_payment"
    assert renames[0].to_name == "execute_payment"
    assert renames[0].details["method"] == "levenshtein_tokens"

    assert len(deletes) == 1
    assert deletes[0].name == "to_be_deleted"

    assert len(adds) == 1
    assert adds[0].name == "newly_added"

    assert len(modifies) == 0


def test_modify_function_operators():
    extractor = TransformExtractor()

    old_symbols = [
        CodeSymbol(
            name="calculate_tax",
            type=SymbolType.FUNCTION,
            start_line=5,
            end_line=8,
            signature="(subtotal)",
            body="def calculate_tax(subtotal):\n    return subtotal * 0.1",
            structural_tokens=["return_statement"],
        )
    ]

    new_symbols = [
        CodeSymbol(
            name="calculate_tax",
            type=SymbolType.FUNCTION,
            start_line=5,
            end_line=8,
            signature="(subtotal, rate=0.15)",
            body="def calculate_tax(subtotal, rate=0.15):\n    return subtotal * rate",
            structural_tokens=["return_statement"],
        )
    ]

    operators = extractor.extract_operators("tax.py", old_symbols, new_symbols)

    modifies = [op for op in operators if op.operator == OperatorType.MODIFY_FUNCTION]
    assert len(modifies) == 1
    assert modifies[0].name == "calculate_tax"
    assert modifies[0].details["signature_changed"] is True


def test_formatter_invariant_rename_detection():
    extractor = TransformExtractor()

    old_symbols = [
        CodeSymbol(
            name="process_payment",
            type=SymbolType.FUNCTION,
            start_line=1,
            end_line=4,
            signature="(user, card)",
            body="def process_payment(user, card):\n    validate_card()\n    return user",
            structural_tokens=["expression_statement", "return_statement"],
        )
    ]

    new_symbols = [
        CodeSymbol(
            name="execute_payment",
            type=SymbolType.FUNCTION,
            start_line=1,
            end_line=6,
            signature="(user, card)",
            body="def execute_payment(user, card):\n\n    validate_card()\n\n    return user",
            structural_tokens=["expression_statement", "return_statement"],
        )
    ]

    operators = extractor.extract_operators("billing.py", old_symbols, new_symbols)
    renames = [op for op in operators if op.operator == OperatorType.RENAME_FUNCTION]
    assert len(renames) == 1
    assert renames[0].from_name == "process_payment"
    assert renames[0].to_name == "execute_payment"


def test_block_level_modification_is_orthogonal():
    from gdss.core.transform_types import BodyBlock

    extractor = TransformExtractor()

    old_symbols = [
        CodeSymbol(
            name="process_order",
            type=SymbolType.FUNCTION,
            start_line=1,
            end_line=20,
            signature="()",
            body="...",
            body_blocks=[
                BodyBlock("expression_statement_0", "expression_statement", 2, 4, ["expression_statement"]),
                BodyBlock("return_statement_0", "return_statement", 16, 18, ["return_statement"]),
            ],
            structural_tokens=["expression_statement", "return_statement"],
        )
    ]

    new_symbols = [
        CodeSymbol(
            name="process_order",
            type=SymbolType.FUNCTION,
            start_line=1,
            end_line=20,
            signature="()",
            body="...",
            body_blocks=[
                BodyBlock("expression_statement_0", "expression_statement", 2, 5, ["expression_statement", "comment"]),
                BodyBlock("return_statement_0", "return_statement", 16, 18, ["return_statement"]),
            ],
            structural_tokens=["expression_statement", "return_statement"],
        )
    ]

    operators = extractor.extract_operators("orders.py", old_symbols, new_symbols)
    modifies = [op for op in operators if op.operator == OperatorType.MODIFY_FUNCTION]
    assert len(modifies) == 1
    assert modifies[0].details["changed_blocks"] == ["expression_statement_0"]


def test_levenshtein_token_similarity():
    a = ["if_statement", "return_statement"]
    b = ["if_statement", "return_statement"]
    c = ["while_statement", "return_statement"]
    assert levenshtein_distance(a, b) == 0
    assert normalized_similarity(a, b) == 1.0
    assert normalized_similarity(a, c) < 1.0
