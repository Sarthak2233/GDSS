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
    assert "outside" in result.reason
