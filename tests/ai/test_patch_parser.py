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
