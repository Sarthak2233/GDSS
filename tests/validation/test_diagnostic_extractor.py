"""Unit tests for Diagnostic Extractor & Differential Baseline (Phase 2 of Solution)."""

from __future__ import annotations

from gdss.validation.diagnostic_extractor import (
    DiagnosticEvidence,
    DiagnosticPayload,
    compute_differential_diagnostics,
    parse_test_diagnostics,
)

SAMPLE_PYTEST_FAILURE = """
============================= test session starts ==============================
collected 3 items

tests/integration/test_order_flow.py .F.                                  [100%]

=================================== FAILURES ===================================
________________________ test_complete_checkout_workflow _______________________

    def test_complete_checkout_workflow():
        order = Order(id="123", amount=100)
>       status = execute_payment(order)
E       TypeError: execute_payment() missing 1 required positional argument: 'currency'

order_service.py:84: TypeError
----------------------------- Captured stdout call -----------------------------
Starting payment for order 123...
=========================== short test summary info ============================
FAILED tests/integration/test_order_flow.py::test_complete_checkout_workflow - TypeError: execute_payment() missing 1 required positional argument: 'currency'
========================= 1 failed, 2 passed in 0.12s ==========================
"""

SAMPLE_PYTEST_ASSERTION_FAILURE = """
=================================== FAILURES ===================================
_____________________________ test_payment_amount ______________________________

    def test_payment_amount():
        res = get_total()
>       assert res == 100
E       assert 50 == 100

tests/test_payment.py:42: AssertionError
=========================== short test summary info ============================
FAILED tests/test_payment.py::test_payment_amount - assert 50 == 100
========================= 1 failed in 0.05s ==========================
"""


def test_parse_pytest_diagnostics_type_error():
    payload = parse_test_diagnostics(tool_name="pytest", raw_output=SAMPLE_PYTEST_FAILURE, exit_code=1)

    assert isinstance(payload, DiagnosticPayload)
    assert payload.status == "VALIDATION_FAILED"
    assert payload.total_failed == 1
    assert len(payload.diagnostics) == 1

    diag = payload.diagnostics[0]
    assert diag.test_file == "tests/integration/test_order_flow.py"
    assert diag.test_case == "test_complete_checkout_workflow"
    assert diag.failure_type == "TypeError"
    assert "missing 1 required positional argument" in (diag.expected or "")
    assert "execute_payment" in diag.implicated_symbols
    assert diag.line_number == 84
    assert diag.regression_origin == "INTRODUCED_BY_PATCH"


def test_parse_pytest_diagnostics_assertion_error():
    payload = parse_test_diagnostics(tool_name="pytest", raw_output=SAMPLE_PYTEST_ASSERTION_FAILURE, exit_code=1)

    assert payload.total_failed == 1
    diag = payload.diagnostics[0]
    assert diag.test_file == "tests/test_payment.py"
    assert diag.test_case == "test_payment_amount"
    assert diag.failure_type == "AssertionError"
    assert diag.expected == "100"
    assert diag.actual == "50"
    assert diag.line_number == 42


def test_compute_differential_diagnostics():
    # Base failure: pre-existing failure in tests/test_legacy.py
    base_diag = DiagnosticPayload(
        status="VALIDATION_FAILED",
        total_failed=1,
        tool="pytest",
        diagnostics=[
            DiagnosticEvidence(
                test_file="tests/test_legacy.py",
                test_case="test_old_feature",
                failure_type="AssertionError",
                regression_origin="INTRODUCED_BY_PATCH",
            )
        ],
    )

    # Candidate has both the pre-existing failure AND a new patch failure
    candidate_diag = DiagnosticPayload(
        status="VALIDATION_FAILED",
        total_failed=2,
        tool="pytest",
        diagnostics=[
            DiagnosticEvidence(
                test_file="tests/test_legacy.py",
                test_case="test_old_feature",
                failure_type="AssertionError",
                regression_origin="INTRODUCED_BY_PATCH",
            ),
            DiagnosticEvidence(
                test_file="tests/test_payment.py",
                test_case="test_new_currency",
                failure_type="TypeError",
                regression_origin="INTRODUCED_BY_PATCH",
            ),
        ],
    )

    diff = compute_differential_diagnostics(candidate_diag=candidate_diag, baseline_diag=base_diag)

    by_test = {d.test_case: d for d in diff.diagnostics}
    # Pre-existing failure should be suppressed/tagged as PRE_EXISTING_BASELINE
    assert by_test["test_old_feature"].regression_origin == "PRE_EXISTING_BASELINE"
    # New failure introduced by patch must be tagged INTRODUCED_BY_PATCH
    assert by_test["test_new_currency"].regression_origin == "INTRODUCED_BY_PATCH"


SAMPLE_VITEST_FAILURE = """
 FAIL  src/checkout.test.ts > Checkout Flow > should calculate total with tax
AssertionError: expected 50 to be 100 // Object.is equality

- Expected
+ Received

- 100
+ 50

 ❯ src/checkout.test.ts:45:12
"""

SAMPLE_CARGO_FAILURE = """
failures:

---- tests::test_calculate_total stdout ----
thread 'tests::test_calculate_total' panicked at tests/test_calc.rs:32:9:
assertion `left == right` failed
  left: 50
 right: 100
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace

failures:
    tests::test_calculate_total

test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 0 filtered out
"""

SAMPLE_GOTEST_FAILURE = """
=== RUN   TestProcessPayment
    payment_test.go:45: expected amount 100, got 50
--- FAIL: TestProcessPayment (0.01s)
FAIL
exit status 1
FAIL	github.com/gdss/payment	0.012s
"""

SAMPLE_DOTNET_FAILURE = """
Starting test execution, please wait...
Failed TestProcessPayment [15 ms]
Error Message:
 Assert.Equal() Failure
 Expected: 100
 Actual:   50
Stack Trace:
   at Tests.PaymentTests.TestProcessPayment() in /workspace/src/PaymentTests.cs:line 28

Total tests: 1. Passed: 0. Failed: 1.
"""


def test_parse_vitest_diagnostics():
    payload = parse_test_diagnostics(tool_name="vitest", raw_output=SAMPLE_VITEST_FAILURE, exit_code=1)

    assert payload.status == "VALIDATION_FAILED"
    assert payload.total_failed == 1
    diag = payload.diagnostics[0]
    assert "src/checkout.test.ts" in diag.test_file
    assert diag.test_case == "should calculate total with tax"
    assert diag.actual == "50"
    assert diag.expected == "100"
    assert diag.line_number == 45


def test_parse_cargo_rust_diagnostics():
    payload = parse_test_diagnostics(tool_name="cargo test", raw_output=SAMPLE_CARGO_FAILURE, exit_code=101)

    assert payload.status == "VALIDATION_FAILED"
    assert payload.total_failed == 1
    diag = payload.diagnostics[0]
    assert diag.test_file == "tests/test_calc.rs"
    assert diag.test_case == "tests::test_calculate_total"
    assert diag.actual == "50"
    assert diag.expected == "100"
    assert diag.line_number == 32


def test_parse_go_test_diagnostics():
    payload = parse_test_diagnostics(tool_name="go test", raw_output=SAMPLE_GOTEST_FAILURE, exit_code=1)

    assert payload.status == "VALIDATION_FAILED"
    assert payload.total_failed == 1
    diag = payload.diagnostics[0]
    assert diag.test_file == "payment_test.go"
    assert diag.test_case == "TestProcessPayment"
    assert "expected amount 100" in (diag.expected or "")
    assert diag.line_number == 45


def test_parse_dotnet_diagnostics():
    payload = parse_test_diagnostics(tool_name="dotnet test", raw_output=SAMPLE_DOTNET_FAILURE, exit_code=1)

    assert payload.status == "VALIDATION_FAILED"
    assert payload.total_failed == 1
    diag = payload.diagnostics[0]
    assert "PaymentTests.cs" in diag.test_file
    assert diag.test_case == "TestProcessPayment"
    assert diag.expected == "100"
    assert diag.actual == "50"
    assert diag.line_number == 28


