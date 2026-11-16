"""Unit tests for Multi-File Coordinated Patch Packaging & Atomic Rollback (Phase 3 of Solution)."""

from __future__ import annotations

import json
from pathlib import Path

from gdss.validation.guarded_apply import (
    apply_suggestion,
    parse_multi_file_unified_diff,
    rollback_suggestion,
)

SAMPLE_MULTI_FILE_DIFF = """
diff --git a/payment_service.py b/payment_service.py
--- a/payment_service.py
+++ b/payment_service.py
@@ -1,3 +1,3 @@
-def process_payment(order):
+def execute_payment(order, currency='USD'):
     return True
diff --git a/checkout.py b/checkout.py
--- a/checkout.py
+++ b/checkout.py
@@ -1,3 +1,3 @@
 def checkout_flow():
-    return process_payment(order)
+    return execute_payment(order, currency='USD')
"""

SAMPLE_MULTI_FILE_SYNTAX_ERROR_DIFF = """
diff --git a/payment_service.py b/payment_service.py
--- a/payment_service.py
+++ b/payment_service.py
@@ -1,3 +1,3 @@
-def process_payment(order):
+def execute_payment(order, currency='USD'):
     return True
diff --git a/checkout.py b/checkout.py
--- a/checkout.py
+++ b/checkout.py
@@ -1,3 +1,3 @@
 def checkout_flow():
-    return process_payment(order)
+    return execute_payment(order, currency=:::INVALID_SYNTAX:::)
"""


def test_parse_multi_file_unified_diff():
    diffs = parse_multi_file_unified_diff(SAMPLE_MULTI_FILE_DIFF)

    assert "payment_service.py" in diffs
    assert "checkout.py" in diffs
    assert "execute_payment(order, currency='USD')" in diffs["payment_service.py"]
    assert "execute_payment(order, currency='USD')" in diffs["checkout.py"]


def test_atomic_multi_file_apply_success(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    pay_file = tmp_path / "payment_service.py"
    check_file = tmp_path / "checkout.py"

    pay_file.write_text("def process_payment(order):\n    return True\n", encoding="utf-8")
    check_file.write_text(
        "def checkout_flow():\n    return process_payment(order)\n", encoding="utf-8"
    )

    sug_dir = tmp_path / ".gdss" / "suggestions"
    sug_dir.mkdir(parents=True)
    suggestion_id = "sug_multi_001"
    sug_data = {
        "id": suggestion_id,
        "file_path": "payment_service.py",
        "affected_files": ["payment_service.py", "checkout.py"],
        "patch_combinations": [
            {
                "strategy": "coordinated_multi_file",
                "label": "Coordinated Multi-File Convergence",
                "patch_text": SAMPLE_MULTI_FILE_DIFF,
            }
        ],
    }
    (sug_dir / f"{suggestion_id}.json").write_text(json.dumps(sug_data), encoding="utf-8")

    result = apply_suggestion(suggestion_id=suggestion_id, repo_root=tmp_path)

    assert result.success is True
    assert "def execute_payment(order, currency='USD'):" in pay_file.read_text(encoding="utf-8")
    assert "execute_payment(order, currency='USD')" in check_file.read_text(encoding="utf-8")

    # Verify rollback restores both files
    rb_res = rollback_suggestion(suggestion_id=suggestion_id, repo_root=tmp_path)
    assert rb_res.success is True
    assert "def process_payment(order):" in pay_file.read_text(encoding="utf-8")
    assert "process_payment(order)" in check_file.read_text(encoding="utf-8")


def test_atomic_multi_file_rollback_on_syntax_error(tmp_path: Path):
    (tmp_path / ".git").mkdir()
    pay_file = tmp_path / "payment_service.py"
    check_file = tmp_path / "checkout.py"

    orig_pay = "def process_payment(order):\n    return True\n"
    orig_check = "def checkout_flow():\n    return process_payment(order)\n"
    pay_file.write_text(orig_pay, encoding="utf-8")
    check_file.write_text(orig_check, encoding="utf-8")

    sug_dir = tmp_path / ".gdss" / "suggestions"
    sug_dir.mkdir(parents=True)
    suggestion_id = "sug_multi_corrupt"
    sug_data = {
        "id": suggestion_id,
        "file_path": "payment_service.py",
        "affected_files": ["payment_service.py", "checkout.py"],
        "patch_combinations": [
            {
                "strategy": "coordinated_multi_file",
                "label": "Coordinated Multi-File Convergence",
                "patch_text": SAMPLE_MULTI_FILE_SYNTAX_ERROR_DIFF,
            }
        ],
    }
    (sug_dir / f"{suggestion_id}.json").write_text(json.dumps(sug_data), encoding="utf-8")

    result = apply_suggestion(suggestion_id=suggestion_id, repo_root=tmp_path)

    # Must fail because checkout.py has syntax corruption
    assert result.success is False
    assert "syntax" in (result.error or "").lower()

    # ALL files must be restored to their original state (all-or-nothing atomicity)
    assert pay_file.read_text(encoding="utf-8") == orig_pay
    assert check_file.read_text(encoding="utf-8") == orig_check

