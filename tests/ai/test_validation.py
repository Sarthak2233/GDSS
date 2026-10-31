from gdss.ai.types import Suggestion
from gdss.ai.validation import validate_patch


def _suggestion() -> Suggestion:
    return Suggestion(
        kind="conflict",
        file_path="src/payments.py",
        line_start=10,
        line_end=20,
        symbol_id="src/payments.py::process",
        operator="modify_function",
        action="review",
        rationale="overlap",
        reason=("both branches modify process",),
        confidence=0.7,
    )


def test_validate_patch_accepts_a_hunk_wholly_inside_the_symbol_anchor():
    patch = """--- a/src/payments.py
+++ b/src/payments.py
@@ -12,2 +12,2 @@
-    return amount
+    return amount * 2
"""

    result = validate_patch(_suggestion(), patch)

    assert result.valid is True
    assert result.reason is None


def test_validate_patch_rejects_a_hunk_outside_the_symbol_anchor():
    patch = """--- a/src/payments.py
+++ b/src/payments.py
@@ -25,1 +25,1 @@
-old = True
+old = False
"""

    result = validate_patch(_suggestion(), patch)

    assert result.valid is False
    assert result.reason is not None and "outside" in result.reason


def test_validate_patch_accepts_clean_replacement_block_with_valid_syntax():
    code = "def process(amount: float) -> float:\n    return amount * 2.5\n"
    original = "def process(amount: float) -> float:\n    return amount\n"

    result = validate_patch(_suggestion(), code, original_code=original)
    assert result.valid is True
    assert result.synthesized_diff is not None
    assert "--- a/src/payments.py" in result.synthesized_diff


def test_validate_patch_rejects_clean_replacement_block_with_syntax_error():
    broken_code = "def process(amount: float) -> float:\n    return amount * (\n"
    result = validate_patch(_suggestion(), broken_code)
    assert result.valid is False
    assert "syntax error" in (result.reason or "").lower()
