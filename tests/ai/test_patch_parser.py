import pytest

from gdss.ai.patch_parser import PatchParseError, parse_strategy_patches


def test_parse_strategy_patches_returns_named_unified_diffs():
    response = """--- patch: payments.py:2-2 (strategy: keep i) ---
--- a/payments.py
+++ b/payments.py
@@ -2,1 +2,1 @@
-    return amount * 2
+    return amount * 4
--- end ---
"""

    patches = parse_strategy_patches(response, expected_strategies=("keep i",))

    assert patches["keep i"].startswith("--- a/payments.py")


def test_parse_strategy_patches_rejects_unrequested_or_duplicate_strategies():
    response = """--- patch: payments.py:2-2 (strategy: keep i) ---
--- a/payments.py
+++ b/payments.py
@@ -2,1 +2,1 @@
-    return amount * 2
+    return amount * 4
--- end ---
--- patch: payments.py:2-2 (strategy: keep i) ---
--- a/payments.py
+++ b/payments.py
@@ -2,1 +2,1 @@
-    return amount * 2
+    return amount * 5
--- end ---
"""

    with pytest.raises(PatchParseError, match="duplicate"):
        parse_strategy_patches(response, expected_strategies=("keep i",))


def test_clean_markdown_fence():
    from gdss.ai.patch_parser import clean_markdown_fence

    fenced = "```python\ndef foo():\n    return 1\n```"
    assert clean_markdown_fence(fenced) == "def foo():\n    return 1"

    plain = "def foo():\n    return 1"
    assert clean_markdown_fence(plain) == plain


def test_replacement_to_unified_diff():
    from gdss.ai.patch_parser import replacement_to_unified_diff

    original = "def calculate(x):\n    return x\n"
    replacement = "def calculate(x, factor=1):\n    return x * factor\n"
    diff = replacement_to_unified_diff(
        replacement_code=replacement,
        original_code=original,
        file_path="app/math.py",
        line_start=15,
        line_end=16,
    )

    assert "--- a/app/math.py" in diff
    assert "+++ b/app/math.py" in diff
    assert "@@ -15," in diff
    assert "+def calculate(x, factor=1):" in diff
    assert "-def calculate(x):" in diff


def test_extract_patch_or_replacement():
    from gdss.ai.patch_parser import extract_patch_or_replacement

    diff_text = """```diff
--- a/foo.py
+++ b/foo.py
@@ -1,1 +1,1 @@
-a
+b
```"""
    content, kind = extract_patch_or_replacement(diff_text)
    assert kind == "unified_diff"
    assert content.startswith("--- a/foo.py")

    code_text = """```python
def foo():
    return 42
```"""
    content, kind = extract_patch_or_replacement(code_text)
    assert kind == "replacement_block"
    assert "def foo():" in content
